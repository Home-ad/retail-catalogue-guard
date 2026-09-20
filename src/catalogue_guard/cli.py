import argparse
import json
from pathlib import Path

from .download import download_source
from .pipeline import build


def main():
    parser = argparse.ArgumentParser(prog="catalogue-guard")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch")
    fetch.add_argument("source", choices=["products", "prices", "recalls", "all"])
    commands.add_parser("build")
    server = commands.add_parser("serve")
    server.add_argument("--port", type=int, default=8765)
    review = commands.add_parser("review")
    review.add_argument("input", type=Path)
    review.add_argument("--output", type=Path, required=True)
    commands.add_parser("stats")
    demo = commands.add_parser("demo")
    demo.add_argument("--source", type=Path, default=Path("demo"))
    args = parser.parse_args()
    if args.command == "fetch":
        for source in ["products", "prices", "recalls"] if args.source == "all" else [args.source]:
            download_source(source, args.data_dir / "raw")
    elif args.command == "build":
        build(args.data_dir)
    elif args.command == "serve":
        import uvicorn

        from .server import create_app

        uvicorn.run(
            create_app(args.data_dir / "catalogue.duckdb"),
            host="127.0.0.1",
            port=args.port,
        )
    elif args.command == "review":
        from .review import export_csv, review_catalogue

        result = review_catalogue(
            args.data_dir / "catalogue.duckdb",
            args.input.read_text(encoding="utf-8-sig"),
        )
        args.output.parent.mkdir(exist_ok=True, parents=True)
        args.output.write_text(export_csv(result), encoding="utf-8-sig")
        print(json.dumps(result["summary"], indent=2))
    elif args.command == "stats":
        from .analytics import overview

        print(json.dumps(overview(args.data_dir / "catalogue.duckdb")["report"], indent=2))
    elif args.command == "demo":
        from .demo import load_demo

        print(json.dumps(load_demo(args.source, args.data_dir), indent=2))


if __name__ == "__main__":
    main()
