# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import re
import json

class BricolagePipeline(object):
    def process_item(self, input_item, spider):
        print ("Inside pipeline! ")
        item = {
        "title" : input_item ["productname"],
        "price" : self.clear_price(input_item ["productcart"]),
        "img" : self.clear_img(input_item ["img"]),
        "characteristics" : {self.clear_data(k) : self.clear_data(v)
        for k, v in input_item ["characteristics"].items()
        },
        "store_availability" : input_item ["availability"],
        }
        print (item)
        return item
        
    def clear_price(self, price):
        price = re.sub(r'([^0-9,.]*)', '', price)
        seps = [",", "."]
        if any(sep in price[:-1] for sep in seps):
            price = price[0:-1]
        if all(sep in price for sep in seps) or "." in price:
            return price
        return price.replace(",", ".")
        
    def clear_data(self, string):
        string = re.sub(r'[\s]+', '', string)
        return re.search('>([^<>]*)<', string).group(1)
        
    def clear_img(self, string):
        string = re.search('src="([^"]+)"', string).group(1)
        return 'https://mr-bricolage.bg'+string


class JsonWriterPipeline(object):
    def open_spider(self, spider):
        self.file = open('scraped_items.json', 'w')
        # Your scraped items will be saved in the file 'scraped_items.json'.
        # You can change the filename to whatever you want.
        self.file.write("[")

    def close_spider(self, spider):
        self.file.write("]")
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(
            dict(item),
            indent = 4,
            sort_keys = True,
            separators = (',', ': ')
        ) + ",\n"
        self.file.write(line)
        return item
