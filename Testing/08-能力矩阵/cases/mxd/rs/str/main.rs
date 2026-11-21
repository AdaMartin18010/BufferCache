// MX-D RS 客户端冒烟（enrich 第二批 2026-11-21 v3）：std RESP + 8 操作族（零 crates）
// 步骤规格 = [期望, 命令, 参数...]；数组回复递归解析、值空格拼接；runid 每族一次（族内同键）
// 用法: rustc main.rs -o smoke && ./smoke --addr 127.0.0.1:6379 --pass lab-password --ops str,hash
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::net::TcpStream;
use std::time::Duration;

fn read_reply(r: &mut BufReader<TcpStream>) -> Result<String, Box<dyn std::error::Error>> {
    let mut line = String::new();
    r.read_line(&mut line)?;
    let line = line.trim_end().to_string();
    if line.is_empty() {
        return Ok(String::new());
    }
    match line.as_bytes()[0] {
        b'$' => {
            if line == "$-1" {
                return Ok("(nil)".into());
            }
            let mut v = String::new();
            r.read_line(&mut v)?;
            Ok(v.trim_end().to_string())
        }
        b'*' => {
            let n: usize = line[1..].trim().parse().unwrap_or(0);
            if n == 0 {
                return Ok("(empty)".into());
            }
            let mut parts = Vec::new();
            for _ in 0..n {
                parts.push(read_reply(r)?);
            }
            Ok(parts.join(" "))
        }
        _ => Ok(line),
    }
}

fn resp_cmd(s: &mut TcpStream, r: &mut BufReader<TcpStream>, args: &[String]) -> Result<String, Box<dyn std::error::Error>> {
    let mut buf = format!("*{}\r\n", args.len());
    for a in args {
        buf.push_str(&format!("${}\r\n{}\r\n", a.len(), a));
    }
    s.write_all(buf.as_bytes())?;
    read_reply(r)
}

fn ops_table() -> HashMap<&'static str, Vec<Vec<&'static str>>> {
    let mut m = HashMap::new();
    m.insert("str", vec![vec!["+OK", "SET", "{K}", "v1"], vec!["v1", "GET", "{K}"], vec![":1", "DEL", "{K}"], vec!["(nil)", "GET", "{K}"]]);
    m.insert("hash", vec![vec![":1", "HSET", "{K}", "f", "v"], vec!["v", "HGET", "{K}", "f"], vec!["f", "HGETALL", "{K}"], vec![":1", "HDEL", "{K}", "f"]]);
    m.insert("list", vec![vec![":1", "RPUSH", "{K}", "a"], vec![":2", "RPUSH", "{K}", "b"], vec!["a b", "LRANGE", "{K}", "0", "-1"], vec!["a", "LPOP", "{K}"]]);
    m.insert("zset", vec![vec![":1", "ZADD", "{K}", "1", "m"], vec!["1", "ZSCORE", "{K}", "m"], vec!["m", "ZRANGE", "{K}", "0", "-1"]]);
    m.insert("expire", vec![vec!["+OK", "SET", "{K}", "v"], vec![":1", "EXPIRE", "{K}", "100"], vec!["TTL_POS", "TTL", "{K}"], vec![":1", "PERSIST", "{K}"]]);
    m.insert("bitmap", vec![vec![":0", "SETBIT", "{K}", "7", "1"], vec![":1", "GETBIT", "{K}", "7"]]);
    m.insert("stream", vec![vec!["STREAM_ID", "XADD", "{K}", "*", "f", "v"], vec![":1", "XLEN", "{K}"]]);
    m.insert("txlua", vec![vec!["+OK", "EVAL", "return redis.call('set',KEYS[1],'lua1')", "1", "{K}"], vec!["lua1", "GET", "{K}"]]);
    m
}

fn matches(want: &str, got: &str) -> bool {
    match want {
        "TTL_POS" => got.trim_start_matches(':').parse::<f64>().map(|n| n > 0.0).unwrap_or(false),
        "STREAM_ID" => got.chars().next().map(|c| c.is_ascii_digit()).unwrap_or(false),
        _ => got.starts_with(want) || got.contains(want),
    }
}

fn main() {
    let mut addr = "127.0.0.1:6379".to_string();
    let mut pass = String::new();
    let mut ops = "str".to_string();
    let mut it = std::env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "--addr" => addr = it.next().unwrap_or(addr),
            "--pass" => pass = it.next().unwrap_or(pass),
            "--ops" => ops = it.next().unwrap_or(ops),
            _ => {}
        }
    }
    let mut s = match TcpStream::connect_timeout(&addr.parse().expect("addr parse"), Duration::from_secs(5)) {
        Ok(x) => x,
        Err(e) => { println!("CONNECT_FAIL {}", e); std::process::exit(1); }
    };
    let mut r = BufReader::new(match s.try_clone() { Ok(x) => x, Err(e) => { println!("CLONE_FAIL {}", e); std::process::exit(1); } });
    if !pass.is_empty() {
        if let Err(e) = resp_cmd(&mut s, &mut r, &["AUTH".to_string(), pass.clone()]) { println!("AUTH_FAIL {}", e); std::process::exit(1); }
    }
    let table = ops_table();
    let mut total = 0;
    for op in ops.split(',').map(str::trim) {
        let steps = match table.get(op) {
            Some(x) => x,
            None => { println!("UNKNOWN_OP {}", op); std::process::exit(2); }
        };
        let mut fail = 0;
        let runid = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
        for step in steps {
            let want = step[0];
            let args: Vec<String> = step[1..].iter().map(|a| a.replace("{K}", &format!("mxd:rs:{}:{}", op, runid))).collect();
            match resp_cmd(&mut s, &mut r, &args) {
                Ok(ref got) if matches(want, got) => {}
                other => { println!("FAIL rs/{} {:?} got={:?} want={}", op, args, other.map(|x| x), want); fail += 1; }
            }
        }
        if fail == 0 { println!("PASS rs/{} ({} 断言)", op, steps.len()); }
        total += fail;
    }
    std::process::exit(if total > 0 { 1 } else { 0 });
}
