// MX-D GO STR 种子资产：stdlib RESP 客户端冒烟（无外部依赖，规避模块拉取失败）
// 用法: go run main.go -addr 127.0.0.1:6379 -pass lab-password   RC: 0=PASS
package main

import (
	"bufio"
	"flag"
	"fmt"
	"net"
	"os"
	"strings"
	"time"
)

func respCmd(c net.Conn, r *bufio.Reader, args ...string) (string, error) {
	fmt.Fprintf(c, "*%d\r\n", len(args))
	for _, a := range args {
		fmt.Fprintf(c, "$%d\r\n%s\r\n", len(a), a)
	}
	// 简化解析：单行/块响应取首行语义，足够断言 OK/value/count
	line, err := r.ReadString('\n')
	if err != nil {
		return "", err
	}
	line = strings.TrimRight(line, "\r\n")
	if strings.HasPrefix(line, "$") { // bulk
		if line == "$-1" {
			return "(nil)", nil
		}
		v, err := r.ReadString('\n')
		if err != nil {
			return "", err
		}
		return strings.TrimRight(v, "\r\n"), nil
	}
	return line, nil
}

func main() {
	addr := flag.String("addr", "127.0.0.1:6379", "redis addr")
	pass := flag.String("pass", "", "requirepass")
	flag.Parse()
	c, err := net.DialTimeout("tcp", *addr, 5*time.Second)
	if err != nil {
		fmt.Println("CONNECT_FAIL", err)
		os.Exit(1)
	}
	defer c.Close()
	r := bufio.NewReader(c)
	if *pass != "" {
		if _, err := respCmd(c, r, "AUTH", *pass); err != nil {
			fmt.Println("AUTH_FAIL", err)
			os.Exit(1)
		}
	}
	fail := 0
	check := func(name string, got, wantPrefix string) {
		if !strings.HasPrefix(got, wantPrefix) {
			fmt.Printf("FAIL %s got=%q want prefix %q\n", name, got, wantPrefix)
			fail++
		} else {
			fmt.Printf("PASS %s -> %s\n", name, got)
		}
	}
	check("SET", must(respCmd(c, r, "SET", "mxd:go:str", "v1")), "+OK")
	check("GET", must(respCmd(c, r, "GET", "mxd:go:str")), "v1")
	check("DEL", must(respCmd(c, r, "DEL", "mxd:go:str")), ":1")
	check("GET-after-DEL", must(respCmd(c, r, "GET", "mxd:go:str")), "(nil)")
	if fail > 0 {
		os.Exit(1)
	}
	fmt.Println("GO-STR-SMOKE-PASS")
}

func must(s string, err error) string {
	if err != nil {
		fmt.Println("IO_FAIL", err)
		os.Exit(1)
	}
	return s
}
