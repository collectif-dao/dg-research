# Lido Dual Governance Model

A modular agent based model of Lido Dual Governance system, based on the open-source Solidity implementation of Dual Governance system.

Implements the official Lido Dual Governance [specifications](https://github.com/lidofinance/dual-governance/)

This model utilize an open-source Python library [radCAD](https://github.com/CADLabs/radCAD), an extension to [cadCAD](https://cadcad.org/).

## Model Architecture

WIP: Would be provided in later stage

## Model Assumptions

The model implements the official Lido Dual Governance Specification wherever possible, but rests on a few default actor-level assumptions detailed in the [ASSUMPTIONS.md](ASSUMPTIONS.md) document.

## Environment Setup

1. Clone or download this GitHub repository by running `git clone https://github.com/collectif-dao/dg-research.git` in your terminal.
2. Set up your development environment using Anaconda virtual environment:

## Setting Up an Anaconda Virtual Environment

This guide provides step-by-step instructions on how to set up an Anaconda virtual environment for your project. This documentation assumes that you have Anaconda or Miniconda installed on your system.

### 1. Install Anaconda or Miniconda

If you haven't already installed Anaconda or Miniconda, you can download and install it from the official website:

- [Anaconda](https://www.anaconda.com/products/distribution)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

### 2. Create a New Virtual Environment

To create a new virtual environment, use the following command:

```bash
conda create --name lido-dual-governance-abm
```

### 3. Activate the Virtual Environment

To start using the virtual environment, you need to activate it:

```bash
conda activate myenv
```

### 4. Install Required Packages

Once the environment is activated, you can install the necessary packages. You can install the packages using:

```bash
conda install --file requirements.txt
```

Or alternatively using pip:

```bash
pip install -r requirements.txt
```

Or by using a target from `Makefile`:

```bash
make install
```

## Running Simulations

The `Makefile` provides a set of targets to automate the execution of different simulations.

To run all the defined simulations in sequence, use the following command:

```bash
make run_simulations
```

This will execute the all existing simulations in order.

Or you can run a specific simulation by it's name, for example:

```bash
make model_validation
```

## Development

Current model code has been tested on Python 3.12 version, so please let us know if you're facing issues with older versions.

### Testing model and specifications

We use Pytest to test the model code, as well as the notebooks.

To execute the Pytest tests simply run:

```bash
pytest
```

### Benchmarking

We use [Scalene](https://github.com/plasma-umass/scalene) to benchmark CPU/GPU and Memory consumption. After running a benchmark Scalene will open a Web UI with details on the simulation consumption.

> **Note**
>
> If you're running on Windows you'll be able to see reports only on CPU and GPU profiling, but not memory or copy profiling.

The following command runs Scalene on a provided benchmark.

```bash
scalene benchmarks/memory_profiling.py
```
