use std::env;
use std::fs;
use std::path::PathBuf;
use minisign_verify::{PublicKey, Signature};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 4 {
        eprintln!(
            "Usage: {} <public-key-file> <signature-file> <data-file>",
            args[0]
        );
        std::process::exit(1);
    }

    let pk_path = PathBuf::from(&args[1]);
    let sig_path = PathBuf::from(&args[2]);
    let data_path = PathBuf::from(&args[3]);

    let pk = PublicKey::from_file(&pk_path)?;
    let sig = Signature::from_file(&sig_path)?;
    let data = fs::read(&data_path)?;

    match pk.verify(&data, &sig, false) {
        Ok(()) => {
            println!("Signature verification: OK");
            Ok(())
        }
        Err(e) => {
            eprintln!("Signature verification failed: {}", e);
            std::process::exit(1);
        }
    }
}
