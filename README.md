## Mr-bricolage.bg items scraper

Based on a given category scraps items from [Mr Bricolage](https://mr-bricolage.bg).

### Requirements:

* Python 3+
* Scrapy

### Installation:

Install the dependencies:
```
pip install -r requirements.txt
```
If you have troubles installing Scrapy, check their [documentation](https://doc.scrapy.org/en/latest/intro/install.html).
You might need some additional dependencies.
Note: On Debian/Ubuntu if you get a missing ```sqllite3``` error you might need to install ```libsqlite3-dev``` as well:
```
sudo apt-get install libsqlite3-dev
```

### Usage:

From the command line run:

``` 
scrapy crawl bricolage -a cat=CAT_NAME_WITHOUT_WHITESPACES
```
where ```CAT_NAME_WITHOUT_WHITESPACES``` is the name of the category you want to scrap with a dash "-"
instead of white spaces.

The output will be stored to ```scraped_items.json``` in the root folder. 

Alternatively, you can store them elsewhere using:
``` 
scrapy crawl bricolage -a cat=CAT_NAME_WITHOUT_WHITESPACES -o FILE_NAME.json
```

### Note:

The scraper currently works without proxies. For regular usage seriously consider adding proxies.
