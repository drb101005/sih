from maintenance_optimizer.pipeline import OptimisationPipeline

if __name__ == "__main__":
    result = OptimisationPipeline("data").run_batch()
    print(result["optimizer"])
    print(result["validation"])
    print(result["schedule"].head(20).to_string(index=False))
