import click

@click.group()
@click.argument("foo")
def main(foo):
    print("Main function")    

if __name__ == "__main__":
    main()