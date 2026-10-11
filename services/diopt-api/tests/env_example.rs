use std::net::Ipv4Addr;

/// The documented LAN example must be an address the API accepts (main.rs requires a private IPv4).
#[test]
fn documented_lan_ip_example_is_private() {
    let example = include_str!("../.env.example");
    let value = example
        .lines()
        .find_map(|line| line.trim_start_matches("# ").strip_prefix("DIOPT_LAN_IP="))
        .expect("DIOPT_LAN_IP example present");
    let address: Ipv4Addr = value.trim().parse().expect("valid IPv4");
    assert!(address.is_private(), "{address} is not an RFC 1918 address");
}
