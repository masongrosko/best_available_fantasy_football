---
title: "Setup Hugo Locally"
description: "How to setup Hugo locally to help test before contributing."
weight: 50
---

I am using hugo to create the web documentation for this project. To contribute, you do not need Hugo installed locally, however it makes it a lot easier to visualize your changes when you can test them before pushing them.

## MacOS

```bash
brew install hugo
brew install go
brew install nodejs
npm install -g postcss postcss-cli autoprefixer
```

## Windows

Get a package manager, to make this a lot easier. I use [scoop](https://scoop.sh/).

### Install scoop

```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser # Optional: Needed to run a remote script the first time
irm get.scoop.sh | iex
```

### Install everything for hugo

```bash
scoop install git
scoop install hugo-extended
scoop install go
scoop install nodejs
npm install -g postcss postcss-cli autoprefixer
```

If you already have the things installed, its a good idea to update them. Use `update` instead of `install` in all the appropriate commands.

## Test

```bash
cd github/repo/path
cd docs
hugo server
```

Grab the url from the terminal and open it in the browser.
