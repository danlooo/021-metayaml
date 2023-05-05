#!/usr/bin/env python

import click

def meta_add(a, b):
    return(a + b)

@click.group()
def main():
    pass

if __name__ == "__main__":
    main()
