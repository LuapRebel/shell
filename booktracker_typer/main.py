import typer

from conn import CONN


def main():
    print("Booktracker Main...")


if __name__ == "__main__":
    typer.run(main)
    CONN.close()
