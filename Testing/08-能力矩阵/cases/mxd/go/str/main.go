// MX-D GO 客户端冒烟（enrich 第二批 2026-11-21 v2）：stdlib RESP + 8 操作族参数化
// 步骤规格 = [期望, 命令, 参数...]（{K}=每族唯一键占位；期望支持子串/TTL_POS/STREAM_ID）
// 用法: go run main.go -addr 127.0.0.1:6379 -pass lab-password -ops str,hash   RC: 0=PASS
package main

import (
	"bufio"
	"flag"
	"fmt"
	"net"
	"os"
	"strconv"
	"strings"
	"time"
)

var OPS = map[string][][]string{
	"str":    {{"+OK", "SET", "{K}", "v1"}, {"v1", "GET", "{K}"}, {":1", "DEL", "{K}"}, {"(nil)", "GET", "{K}"}},
	"hash":   {{":1", "HSET", "{K}", "f", "v"}, {"v", "HGET", "{K}", "f"}, {"f", "HGETALL", "{K}"}, {":1", "HDEL", "{K}", "f"}},
	"list":   {{":1", "RPUSH", "{K}", "a"}, {":2", "RPUSH", "{K}", "b"}, {"a b", "LRANGE", "{K}", "0", "-1"}, {"a", "LPOP", "{K}"}},
	"zset":   {{":1", "ZADD", "{K}", "1", "m"}, {"1", "ZSCORE", "{K}", "m"}, {"m", "ZRANGE", "{K}", "0", "-1"}},
	"expire": {{"+OK", "SET", "{K}", "v"}, {":1", "EXPIRE", "{K}", "100"}, {"TTL_POS", "TTL", "{K}"}, {":1", "PERSIST", "{K}"}},
	"bitmap": {{":0", "SETBIT", "{K}", "7", "1"}, {":1", "GETBIT", "{K}", "7"}},
	"stream": {{"STREAM_ID", "XADD", "{K}", "*", "f", "v"}, {":1", "XLEN", "{K}"}},
	"txlua":  {{"+OK", "EVAL", "return redis.call('set',KEYS[1],'lua1')", "1", "{K}"}, {"lua1", "GET", "{K}"}},
}

// readReply 解析单行/块/整数/数组（数组递归读 N 元素，值以空格拼接）
func readReply(r *bufio.Reader) (string, error) {
	line, err := r.ReadString('\n')
	if err != nil {
		return "", err
	}
	line = strings.TrimRight(line, "\r\n")
	if len(line) == 0 {
		return "", nil
	}
	switch line[0] {
	case '$':
		if line == "$-1" {
			return "(nil)", nil
		}
		v, err := r.ReadString('\n')
		if err != nil {
			return "", err
		}
		return strings.TrimRight(v, "\r\n"), nil
	case '*':
		n, _ := strconv.Atoi(line[1:])
		if n <= 0 {
			return "(empty)", nil
		}
		parts := make([]string, 0, n)
		for i := 0; i < n; i++ {
			v, err := readReply(r)
			if err != nil {
				return "", err
			}
			parts = append(parts, v)
		}
		return strings.Join(parts, " "), nil
	default:
		return line, nil
	}
}

func respCmd(c net.Conn, r *bufio.Reader, args ...string) (string, error) {
	fmt.Fprintf(c, "*%d\r\n", len(args))
	for _, a := range args {
		fmt.Fprintf(c, "$%d\r\n%s\r\n", len(a), a)
	}
	return readReply(r)
}

func match(want, got string) bool {
	switch want {
	case "TTL_POS":
		n, err := strconv.ParseFloat(strings.TrimPrefix(got, ":"), 64)
		return err == nil && n > 0
	case "STREAM_ID":
		return len(got) > 0 && got[0] >= '0' && got[0] <= '9'
	default:
		return strings.HasPrefix(got, want) || strings.Contains(got, want)
	}
}

func runOp(c net.Conn, r *bufio.Reader, lang, op string) int {
	fail := 0
	runid := time.Now().UnixNano() // 每次 runOp 一次：族内所有命令共用同键
	for _, step := range OPS[op] {
		want, args := step[0], step[1:]
		for i := range args {
			args[i] = strings.ReplaceAll(args[i], "{K}", fmt.Sprintf("mxd:%s:%s:%d", lang, op, runid))
		}
		got, err := respCmd(c, r, args...)
		if err != nil || !match(want, got) {
			fmt.Printf("FAIL %s/%s %v got=%q want=%q\n", lang, op, args, got, want)
			fail++
		}
	}
	if fail == 0 {
		fmt.Printf("PASS %s/%s (%d 断言)\n", lang, op, len(OPS[op]))
	}
	return fail
}

func main() {
	addr := flag.String("addr", "127.0.0.1:6379", "redis addr")
	pass := flag.String("pass", "", "requirepass")
	ops := flag.String("ops", "str", "逗号分隔: str,hash,list,zset,expire,bitmap,stream,txlua")
	flag.Parse()
	conn, err := net.DialTimeout("tcp", *addr, 5*time.Second)
	if err != nil {
		fmt.Println("CONNECT_FAIL", err)
		os.Exit(1)
	}
	defer conn.Close()
	rd := bufio.NewReader(conn)
	if *pass != "" {
		if _, err := respCmd(conn, rd, "AUTH", *pass); err != nil {
			fmt.Println("AUTH_FAIL", err)
			os.Exit(1)
		}
	}
	total := 0
	for _, op := range strings.Split(*ops, ",") {
		op = strings.TrimSpace(op)
		if _, ok := OPS[op]; !ok {
			fmt.Println("UNKNOWN_OP", op)
			os.Exit(2)
		}
		total += runOp(conn, rd, "go", op)
	}
	if total > 0 {
		os.Exit(1)
	}
	fmt.Println("GO-SMOKE-PASS")
}
