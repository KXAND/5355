# Readme

this is the submission files of COMP 5355 Project 7.

the code requires python3 and following lib:

- Playwright
- BeautifulSoup
- aiofiles

you can install by run

```bash
pip install playwright beautifulsoup4 aiofiles
```

then run

```bash
playwright install
```

there is the explanation of our files:

- `playwrightTest.py`: access different websites and output data into `output/` directory;
- `analyzer.py`: analyzz the data and output result into `analysis/` directory;
- `utils.py`: some important function for `playwrightTest.py` and `analyzer.py`
- `const.py`: configurations and consts, for example, you can configure the output directory path.
- `top100.csv`: a websites list, which actually contains 150 websites.
- `input/`: input files
- `final-result.csv`: the final result.

please note that the final result still need manually replenished and checked. 
