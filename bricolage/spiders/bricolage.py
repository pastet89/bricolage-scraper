from scrapy import Spider, Request
from scrapy.linkextractors import LinkExtractor
from scrapy.http import FormRequest
import re
import json
import sys
"""
Requirement:  libsqlite3-dev

https://doc.scrapy.org/en/latest/topics/request-response.html
response.text
response.url
response.body
b2str ????
ProductItem() instead of dictionary 
https://www.youtube.com/watch?v=4I6Xg6Y17qs
"""

class QuotesSpider(Spider):
    
    name = "bricolage"
    category = None
    category_url = None
    found_subcat = 0
    item_id = 0
    passed_first_results_page = False
    tmp = []
    results = []
    home_url = 'https://mr-bricolage.bg'
    longitude = None
    latitude = None
        
    def __init__(self, category=None):
        if category is None:
            self.alert("Usage: scrapy crawl bricolage -a category=CAT_NAME_WITHOUT_WHITESPACES")
        self.category = category.replace("-", " ")
    
    def start_requests(self):
        self.start_urls = [
             self.home_url,
            'https://mr-bricolage.bg/wro/all_responsive.js'
        ]
        for priority, url in enumerate(self.start_urls):
            yield Request(url=url, priority=priority, callback=self.parse)
        
        
    def parse(self, response):
        if self.longitude is None:
            page_source = self.b2str(response.body, "body")
            try:
                self.latitude = str(format(re.search('latitude:(\-?[0-9]{1,2}\.?[0-9]*)', 
                page_source).group(1)))
                self.longitude = str(format(re.search('longitude:(\-?[0-9]{1,3}\.?[0-9]*)', 
                page_source).group(1)))
            except AttributeError as e:
                print (e)
                self.alert("\nCan't extract lat/long coordinates, items availability will not be parsed ", False)
            yield None
        else:
            main_categories = LinkExtractor(restrict_xpaths=u'//span[@class="yCmsComponent" and ./a[@class="item"]]').\
            extract_links(response)
            main_categories = [self.b2str(main_category.url) for main_category in main_categories]
            for main_category in main_categories:
                if self.found_subcat == 1: break
                yield Request(url=main_category, callback=self.parse_inner_pages)

    def parse_inner_pages(self, response):
        categories = LinkExtractor(restrict_css='[title="%s"]' % self.category).\
        extract_links(response)
        if len(categories) == 1:
            self.found_subcat = 1
            category_url = self.b2str(categories[0].url)
            print("Found cat!", flush=True)
            with open("store.txt", "w") as f:
                f.write(category_url)
                print ("Storing target URL! ", flush=True)
            yield Request(url=category_url, callback=self.parse_items_pages)
    
    def parse_items_pages(self, response):
        print("Parsing items " + self.b2str(response.url), flush=True)
        for item in LinkExtractor(restrict_xpaths=u'//div[@class="product"]//a[contains(@href, "/p/") and @title]').extract_links(response):
            yield Request(self.b2str(item.url), callback=self.parse_item)
        if not self.passed_first_results_page:
            self.passed_first_results_page = True
            page_num_url_init_string = response.url.replace(self.start_urls[0], "") + "?q=%3Arelevance&page="
            pages = LinkExtractor(restrict_xpaths=u'//a[@class="" and contains(@href, "%s")]' % page_num_url_init_string).\
            extract_links(response)
            for page in pages:
                yield Request(self.b2str(page.url), callback=self.parse_items_pages)

        
    def parse_item(self, response):
        #print("Processing " + self.b2str(response.url), flush=True)

        CSRFToken = str(response.css('input[name="CSRFToken"]::attr(value)').extract_first())
        characteristics_keys = response.css('.product-classifications table tr :nth-child(1)').extract()
        characteristics_vals = response.css('.product-classifications table tr :nth-child(2)').extract()
        res = { 'characteristics': dict(zip(characteristics_keys, characteristics_vals)) }
        
        stock_fields = ["cartpage", "entryNumber", "productname", "productcart", "img", "actionurl"]        
        for field in stock_fields:
            res.update({
            field : str(response.css('a[href="#stock"]::attr(data-%s)' % field).extract_first())
            })
        #print ("\n")
        #print ("URL:")
        #print (response.url)
        #print (res)
        self.tmp.append(res)
        frmdata = {
        "locationQuery": "",
        "cartPage": res["cartpage"],
        "entryNumber": res["entryNumber"] if res["entryNumber"] != "None" else "0",
        "latitude": self.latitude,
        "longitude": self.longitude,
        "CSRFToken": CSRFToken
        }
        #print ("Posting data ")
        #print (frmdata)
        #print (self.home_url+res["actionurl"])
        yield FormRequest(self.home_url+res["actionurl"], callback=self.store_availability, method='POST', formdata=frmdata)
    
    def store_availability(self, response):
        #print ("At least being called for item")
        #print ( self.item_id )
        stores = json.loads(response.text)["data"]
        availability = [{store["displayName"]:store["stockPickup"].split("&nbsp;")[0]} for store in stores]
        #print ("Store availability: ", availability)
        self.tmp[self.item_id].update({"availability": availability})
        yield self.tmp[self.item_id]
        self.item_id += 1
        
    
    """
        def __del__(self):
            print ("Total items: %d" % len(self.results))
            print ("Long, Lat", str(self.longitude), str(self.latitude))
            print(self.tmp, flush=True)
    """


        
        
    def b2str(self, byte_str, str_type="url"):
        if str_type != "url":
            return "".join( chr(x) for x in bytearray(byte_str))
        return "".join( chr(x) for x in bytearray(byte_str.encode("utf8")))
           

    def alert(self, msg, is_fatal = True):
        """
        Sends error alerts via SMS or email.
        Modify this function according to your own alert system style.
        
        :param msg: Warning message
        :type msg: string
        
        :param is_fatal: optional - if True, stops the script execution, if False, goes on
        :type is_fatal: bool        
        """
        print (msg)
        pass
        if is_fatal:
            sys.exit()

"""
https://mr-bricolage.bg/bg/%D0%9A%D0%B0%D1%82%D0%B0%D0%BB%D0%BE%D0%B3/%D0%98%D0%BD%D1%81%D1%82%D1%80%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B8/%D0%90%D0%B2%D1%82%D0%BE-%D0%B8-%D0%B2%D0%B5%D0%BB%D0%BE%D0%B0%D0%BA%D1%81%D0%B5%D1%81%D0%BE%D0%B0%D1%80%D0%B8/%D0%92%D0%B5%D0%BB%D0%BE%D0%B0%D0%BA%D1%81%D0%B5%D1%81%D0%BE%D0%B0%D1%80%D0%B8/%D0%A2%D0%A0%D0%9E%D0%9C%D0%91%D0%90/p/922711
https://mr-bricolage.bg/wro/all_responsive.js
ACC.contacts={_autoload:["initPageEvents","bindRadioChange",["bindStoreClick",$(".js-help-center-shops-container").length!=0],"onFileChosen"],storeData:"",storeId:"",coords:
{latitude:42.6641056,longitude:23.3233149}


{'characteristics': {'<td class="attrib">Произход</td>': '<td>\r\n\t\t\t\t\t\t\t\t\tКИТАЙ\xa0\r\n\t\t\t\t\t\t\t\t\t\t</td>', '<td class="attrib">Наименование</td>': '<td>\r\n\t\t\t\t\t\t\t\t\tЖИЛЕТКА СВЕТЛООТРЖ.ОРАНЖЕВА\xa0\r\n\t\t\t\t\t\t\t\t\t\t</td>'}

locationQuery: 
cartPage: false
entryNumber: 0
latitude: 42.6641056
longitude: 23.3233149
CSRFToken: d93af911-f7b1-45c4-a163-4a4554481b86

https://mr-bricolage.bg/store-pickup/922711/pointOfServices

https://stackoverflow.com/questions/30345623/scraping-dynamic-content-using-python-scrapy
pip install scrapy-splash
restrict_xpaths=u'//li[@class="yCmsComponent"]'

* Категория - Велоаксесоари https://mr-bricolage.bg/bg/Каталог/Инструменти/Авто-и-
велоаксесоари/Велоаксесоари/c/006008012
* Нужна информация за изваждане от сайта - заглавие, цена, снимка и характеристики
(под таба на продуктовата страница със същото име)

Бонус изисквания (незадължителни):
* Да се извади информация за &quot;Наличност по магазини&quot; (под таба със същото име, ок
сме със свободен текст без форматиране)
* Да се изчисти цената от букви и излишни символи, и да бъде форматирана в по-
подходящ за обработка формат - например &quot;0.00&quot;
"""


'''
    """
           # Make rules
            self.rules = [
                Rule(LinkExtractor(
                    restrict_xpaths=u'//li[@class="yCmsComponent"]'
                ), callback=self.parse)
            ]
    """


        # Inherit parent
        #super(Spider, self).__init__() 
'''
