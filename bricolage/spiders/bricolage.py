from scrapy import Spider, Request
from scrapy.http import FormRequest
import re
import json
import sys
"""
Requirement:  libsqlite3-dev

https://doc.scrapy.org/en/latest/topics/request-response.html
ProductItem() instead of dictionary 
https://www.youtube.com/watch?v=4I6Xg6Y17qs
"""



class QuotesSpider(Spider):
    
    name = "bricolage"
    cat = None
    cat_url = None
    found_subcat = 0
    item_id = 0
    passed_first_results_page = False
    tmp = []
    home_url = 'https://mr-bricolage.bg'
    longitude = None
    latitude = None
        
    def __init__(self, cat=None):
        if cat is None:
            self.alert("Usage: scrapy crawl bricolage -a cat=CAT_NAME_WITHOUT_WHITESPACES")
        self.cat = cat.replace("-", " ")
    
    def start_requests(self):
        self.start_urls = [
             self.home_url,
            'https://mr-bricolage.bg/wro/all_responsive.js'
        ]
        for priority, url in enumerate(self.start_urls):
            yield Request(url=url, priority=priority, callback=self.parse)
        
        
    def parse(self, response):
        if self.longitude is None:
            for _ in self.parse_long_lat(response):
                yield _
        else:
            for _ in self.parse_cats(response):
                yield _


    def parse_long_lat(self, response):
        try:
            self.latitude = re.search('latitude:(\-?[0-9]{1,2}\.?[0-9]*)', 
            response.text).group(1)
            self.longitude = re.search('longitude:(\-?[0-9]{1,3}\.?[0-9]*)', 
            response.text).group(1)
        except AttributeError as e:
            print (e)
            self.alert("\nCan't extract lat/long coordinates, items availability will not be parsed ", False)
        yield None
    
    """
    START FIX
    """
    
    def parse_cats(self, response):
        main_cats = list(map(self.url, response.css('span.yCmsComponent > a.item::attr(href)').extract() ))
        for main_cat in main_cats:
            if self.found_subcat == 1:
                break
            yield Request(url=main_cat, callback=self.parse_inner_pages)
        
    
    def parse_inner_pages(self, response):
        cats = response.css('a[title="%s"]::attr(href)' % self.cat).extract()
        if cats:
            self.found_subcat = 1
            cat_url = cats[0]
            yield Request(url=self.url(cat_url), callback=self.parse_items_pages)
    """
    END FIX
    """
    
    def parse_items_pages(self, response):
        links = response.css('a[href*="/p/"][title]::attr(href)').extract()
        for link in links:
            yield Request(self.url(link), callback=self.parse_item)
        if not self.passed_first_results_page:
            self.passed_first_results_page = True
            page_num_url_init_string = response.url.replace(self.start_urls[0], "") + "?q=%3Arelevance&page="
            pages = response.css('a[class=""][href*="%s"]::attr(href)' % page_num_url_init_string).extract()
            for page in pages:
                yield Request(self.url(page), callback=self.parse_items_pages)

        
    def parse_item(self, response):
        CSRFToken = str(response.css('input[name="CSRFToken"]::attr(value)').extract_first())
        characteristics_keys = response.css('.product-classifications table tr :nth-child(1)').extract()
        characteristics_vals = response.css('.product-classifications table tr :nth-child(2)').extract()
        res = {
        'characteristics': dict(zip(characteristics_keys, characteristics_vals))
        }
        
        stock_fields = ["cartpage", "entryNumber", "productname", "productcart", "img", "actionurl"]        
        for field in stock_fields:
            res.update({
            field : str(response.css('a[href="#stock"]::attr(data-%s)' % field).extract_first())
            })
        self.tmp.append(res)
        frmdata = {
        "locationQuery": "",
        "cartPage": res["cartpage"],
        "entryNumber": res["entryNumber"] if res["entryNumber"] != "None" else "0",
        "latitude": self.latitude,
        "longitude": self.longitude,
        "CSRFToken": CSRFToken
        }
        yield FormRequest(self.url(res["actionurl"]), callback=self.store_availability, method='POST', formdata=frmdata)
    
    def store_availability(self, response):
        stores = json.loads(response.text)["data"]
        availability = [{store["displayName"]:store["stockPickup"].split("&nbsp;")[0]} for store in stores]
        self.tmp[self.item_id].update({"availability": availability})
        yield self.tmp[self.item_id]
        self.item_id += 1
        
        
    def url(self, link):
        return self.home_url + link
           

    def alert(self, msg, is_fatal = True):
        """
        Sends error alerts via SMS or email.
        Modify this function according to your own alert system style.
        
        :param msg: Warning message
        :type msg: string
        
        :param is_fatal: optional - if True, stops the script execution, if False, goes on
        :type is_fatal: bool        
        """
        pass
        if not is_fatal:
            print(msg)
        else:
            raise Exception(msg)
