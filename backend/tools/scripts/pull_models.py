if __name__ == "__main__":
    from transformers import AutoTokenizer, AutoModelForCausalLM
    print("Downloading Falcon tokenizer and model (this may take a while)...")
    AutoTokenizer.from_pretrained("tiiuae/falcon-7b-instruct")
    AutoModelForCausalLM.from_pretrained("tiiuae/falcon-7b-instruct", trust_remote_code=True)
    print("Done")
