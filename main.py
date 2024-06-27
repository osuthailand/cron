import uvicorn


def main() -> None:
    uvicorn.run("app.boot:api", port=9999)


if __name__ == "__main__":
    main()
