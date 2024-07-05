# Xena OpenAutomation Script Example Library

## Introduction

This repository includes examples of using [XOA Python API](https://docs.xenanetworks.com/projects/xoa-python-api), aka. [xoa-driver](https://pypi.org/project/xoa-driver/)

## What Example Folder Contains

Each folder contains at least three files:

* Python script file - this is where the example code locates
* requirements.txt - dependencies to run the code. You should `pip install -r requirements.txt` to update your Python environment (either global or virtual) to have the necessary dependencies.

## Installing XOA Driver

This section details how to install `xoa-driver`. Installation is necessary to execute scripts that use XOA Python API.

Before installing `xoa-driver`, please make sure your environment has installed `python>=3.10` and `pip`.

You can install the `xoa-driver` to your global or virtual environment for Windows, macOS, and Linux using the commands below. 
```
pip install xoa-driver -U            # latest version
```

Once the `xoa-driver` is installed, you can execute your script.

For the most detailed instructions on how to install the XOA driver, visit our **Getting Started** section of our official XOA documentation here: https://docs.xenanetworks.com/projects/xoa-python-api/en/stable/getting_started/installation.html