from scrapy import Spider, Request
from scrapy.http import FormRequest
from .exceptions import BricolageScraperError
import re
import json


class QuotesSpider(Spider):

    """
    Scraps items from www.mr-bricolage.bg and stores them to scraped_items.json
    To run the spider run from the terminal:
    scrapy crawl bricolage -a cat=CAT_NAME_WITHOUT_WHITESPACES
    Use "-" instead of white spaces for the category parameter.

    Class vars:

    :name: (string) -> spider name, used to run the spider
    :cat: (string) -> category for scraping
    :item_id: (int) -> the sequence number of the scrapped items
    :passed_first_results_page: (bool) -> Indicates if the first
                                page with item results is processed.
                                Used to prevent double loading of the
                                same first page in parse_items_pages()
    :tmp: (list) -> stores the parsed items before sending them to the pipeline
    :home_url: (string) -> Base url of the website to start scraping from
    :long_, lat: (NoneType) -> longitude and latitude coordinates,
                               later set to string type
    :found_cat: (bool) -> Indicates if the target subcategory is found
    """

    name = "bricolage"
    cat = None
    item_id = 0
    passed_first_results_page = False
    tmp = []
    home_url = 'https://mr-bricolage.bg'
    long_ = None
    lat = None
    found_cat = False

    def __init__(self, cat=None):
        """ Assigns the category for parsing to an object var.

        params:
        :param cat: Category name with "-" instead of whitespaces
        :type cat: string """

        if cat is None:
            err = "\nUsage: scrapy crawl bricolage -a cat=CAT_NAME_WITHOUT_WHITESPACES"
            self.alert(err)
        self.cat = cat.replace("-", " ")

    def start_requests(self):
        """ Overwrites the scrapy.Spider start_requests() function and
        parses initialy https://mr-bricolage.bg/wro/all_responsive.js
        with a higher priority. From this page are extracted longitude
        and latitude, which are later needed to get store availability
        of the scraped items. The second page for processing is the main
        page which is later crawled for links and processed further in the
        callbacs chain. """

        self.start_urls = [
            self.home_url,
            self.home_url + '/wro/all_responsive.js'
        ]
        for priority, url in enumerate(self.start_urls):
            yield Request(url=url, priority=priority, callback=self.parse)

    def parse(self, response):
        """ Yields the initial pages parsing from the corresponding function:
        either long/lat extraction or category extraction. """

        if response.url != self.home_url:
            for _ in self.parse_long_lat(response):
                yield _
        else:
            for cat in self.parse_cats(response):
                yield cat

    def parse_long_lat(self, response):
        """ Parses the longitude and latitude needed
        for the store availability processing. """

        try:
            self.lat = re.search('latitude:(\-?[0-9]{1,2}\.?[0-9]*)',
                                 response.text).group(1)
            self.long_ = re.search('longitude:(\-?[0-9]{1,3}\.?[0-9]*)',
                                   response.text).group(1)
        except AttributeError:
            msg = "\nCan't extract lat/long coordinates,"
            msg += " items availability will not be parsed."
            self.alert(msg, False)
        yield None

    def parse_cats(self, response):
        """ Parses the main categories and after that recursively calls itself
         with a meta var, indicating to parse the subcategories of each main
         category until the target category is found. Once the target category
         is found, send its link to parse_items_pages() which extracts the pages
         links and the product items.
        """

        if response.meta.get('cat_type') != "sub_cat":
            cssSelector = 'span.yCmsComponent > a.item::attr(href)'
            main_cats = list(map(self.url, response.css(cssSelector).extract()))
            for main_cat in main_cats:
                yield Request(url=main_cat,
                              callback=self.parse_cats,
                              meta={'cat_type': 'sub_cat'})
        elif not self.found_cat:
            cats = response.css('a[title="%s"]::attr(href)' % self.cat).extract()
            if cats:
                self.found_cat = True
                yield Request(url=self.url(cats[0]), callback=self.parse_items_pages)
        else:
            yield None

    def parse_items_pages(self, response):
        """
        1) Extracts the item links from the first page of the target category
        and sends them for parsing to parse_item()
        2) Extract the next page links of the category from the first page and
        send them recursively to itself for  item link extraction as in 1)
        """

        links = response.css('a[href*="/p/"][title]::attr(href)').extract()
        for link in links:
            yield Request(self.url(link), callback=self.parse_item)
        if not self.passed_first_results_page:
            self.passed_first_results_page = True
            page_num_url_init_string = response.url.replace(self.start_urls[0], "")
            page_num_url_init_string += "?q=%3Arelevance&page="
            pages = response.css('a[class=""][href*="%s"]::attr(href)' %
                                 page_num_url_init_string).extract()
            for page in pages:
                yield Request(self.url(page), callback=self.parse_items_pages)

    def parse_item(self, response):
        """
        Scraps:
        - the item price (called 'productcart' on the site),
        - the item name,
        - the item img url
        - vars needed to be sent to the 'actionurl' in order to get the stores availability
        Stores the items data in self.tmp[]
        Yields:
        The POST request to 'actionurl' for getting the store availability
        """

        csrft_token = str(response.css('input[name="CSRFToken"]::attr(value)').extract_first())
        selector_keys = '.product-classifications table tr :nth-child(1)'
        selector_vals = '.product-classifications table tr :nth-child(2)'
        characteristics_keys = response.css(selector_keys).extract()
        characteristics_vals = response.css(selector_vals).extract()
        res = {
            'characteristics': dict(zip(characteristics_keys,
                                        characteristics_vals))
        }

        stock_fields = [
            "cartpage",
            "entryNumber",
            "productname",
            "productcart",
            "img",
            "actionurl"
        ]
        for field in stock_fields:
            res.update({
                field: str(response.css('a[href="#stock"]::attr(data-%s)' %
                                        field).extract_first())
            })
        self.tmp.append(res)
        frmdata = {
            "locationQuery": "",
            "cartPage": res["cartpage"],
            "entryNumber": res["entryNumber"] if res["entryNumber"] != "None" else "0",
            "latitude": self.lat,
            "longitude": self.long_,
            "CSRFToken": csrft_token
        }
        if self.lat is not None:
            yield FormRequest(self.url(res["actionurl"]),
                              callback=self.store_availability,
                              method='POST', formdata=frmdata)
        else:
            yield self.tmp[self.item_id]
            self.item_id += 1

    def store_availability(self, response):
        """ Scraps the store availability of the item
        and send the item to the pipeline. """

        stores = json.loads(response.text)["data"]
        availability = [
            {
                store["displayName"]:store["stockPickup"].split("&nbsp;")[0]
            } for store in stores
        ]
        self.tmp[self.item_id].update({"availability": availability})
        yield self.tmp[self.item_id]
        self.item_id += 1

    def url(self, link):
        """
        Adds as a prefix the base URL of the target website to the parsed links.

        params:
        :param link: The link to which is added the prefix.
        :type link: string """

        return self.home_url + link

    def alert(self, msg, is_fatal=True):
        """
        Sends error alerts via SMS or email.
        Modify this function according to your own alert system style.

        params:

        :param msg: The error message
        :type msg: string
        :param is_fatal: if True, stops the script execution
                         by raising an error, if False, goes on
        :type is_fatal: bool """

        pass
        if not is_fatal:
            print(msg)
        else:
            raise BricolageScraperError(msg)
