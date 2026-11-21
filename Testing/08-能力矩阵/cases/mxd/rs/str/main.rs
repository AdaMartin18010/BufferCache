# MX-D RS STR 种子资产：std TcpStream RESP 客户端冒烟（无 crates.io 依赖）
# 用法: cargo run -- --addr 127.0.0.1:6379 --pass lab-password   RC: 0=PASS
use std::io::{BufRead, BufReader, Write};
use std::net::TcpStream;
use std::time::Duration;

fn resp_cmd(s: &mut TcpStream, r: &mut BufReader<TcpStream>, args: &[&str]) -> Result<String, Box<dyn std::error::Error>> {
    let mut buf = format!("*{}\r\n", args.len());
    for a in args {
        buf.push_str(&format!("${}\r\n{}\r\n", a.len(), a));
    }
    s.write_all(buf.as_bytes())?;
    let mut line = String::new();
    r.read_line(&mut line)?;
    let line = line.trim_end().to_string();
    if let Some(rest) = line.strip_prefix('$') {
        if rest == "-1" {
            return Ok("(nil)".into());
        }
        let mut v = String::new();
        r.read_line(&mut v)?;
        return Ok(v.trim_end().to_string());
    }
    Ok(line)
}

fn main() {
    let mut addr = "127.0.0.1:6379".to_string();
    let mut pass = String::new();
    let mut it = std::env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "--addr" => addr = it.next().unwrap_or(addr),
            "--pass" => pass = it.next().unwrap_or(pass),
            _ => {}
        }
    }
    let mut s = match TcpStream::connect_timeout(&addr.parse().expect("addr parse"), Duration::from_secs(5)) {
        Ok(x) => x,
        Err(e) => { println!("CONNECT_FAIL {}", e); std::process::exit(1); }
    };
    let mut r = BufReader::new(match s.try_clone() { Ok(x) => x, Err(e) => { println!("CLONE_FAIL {}", e); std::process::exit(1); } });
    if !pass.is_empty() {
        if let Err(e) = resp_cmd(&mut s, &mut r, &["AUTH", &pass]) { println!("AUTH_FAIL {}", e); std::process::exit(1); }
    }
    let mut fail = 0;
    let mut check = |name: &str, got: Result<String, Box<dyn std::error::Error>>, want: &str| {
        match got {
            Ok(g) if g.starts_with(want) => println!("PASS {} -> {}", name, g),
            other => { println!("FAIL {} got={:?} want prefix {}", name, other.map(|x| x), want); fail += 1; }
        }
    };
    check("SET", resp_cmd(&mut s, &mut r, &["SET", "mxd:rs:str", "v1"]), "+OK");
    check("GET", resp_cmd(&mut s, &mut r, &["GET", "mxd:rs:str"]), "v1");
    check("DEL", resp_cmd(&mut s, &mut r, &["DEL", "mxd:rs:str"]), ":1");
    check("GET-after-DEL", resp_cmd(&mut s, &mut r, &["GET", "mxd:rs:str"]), "(nil)");
    std::process::exit(if fail > 0 { 1 } else { 0 });
}
