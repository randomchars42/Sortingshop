#!/usr/bin/env python3

from sortingshop import exiftool

def main():
    with exiftool.ExifToolSingleton():
        print('Nice :)')

if __name__ == '__main__':
    main()
