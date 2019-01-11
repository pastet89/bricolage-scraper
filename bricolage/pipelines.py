# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import re
import json

class BricolagePipeline(object):
    
    def process_item(self, input_item, spider):
        """ Clears the item data and sends it to JsonWriterPipeline
        for an output.
        
        params (passed automatically by Scrapy):
        :input_item: (dict) -> the scraped unprocessed item data
        :spider: (obj) -> the spider instance which has scrapped the data """
        
        item = {
            "title" : input_item ["productname"],
            "price" : self.clear_price(input_item ["productcart"]),
            "img" : self.clear_img(input_item ["img"]),
            "characteristics" : {self.clear_data(k) : self.clear_data(v)
            for k, v in input_item ["characteristics"].items()
            },
            "store_availability" : input_item["availability"] \
            if "availability" in input_item else [],
        }
        del input_item
        print ("Parsed item:", item)
        return item
        
    def clear_price(self, price):
        """ Clears the item price to a format 1,000.00
        
        params:
        :price: (string) -> the item's price """
        
        price = re.sub(r'([^0-9,.]*)', '', price)
        price = price[:-1] if "." == price[-1:] else price
        separators = [".", ","]
        if all(s in price for s in separators):
            return price.replace(",", "")
        elif all(s not in price for s in separators):
            return price + ".00"
        elif "," in price and "." not in price:
            return price.replace(",", ".")
        else:
            return price

            
        
        
    def clear_data(self, string):
        """ Clears the item store availability keys and values.
        
        params:
        :string: (string) -> the string for processing """
        
        string = re.sub(r'[\s]+', '', string)
        return re.search('>([^<>]*)<', string).group(1)
        
    def clear_img(self, img_str):
        """ Extracts the item img link
        
        params:
        :img_str: (string) -> the string, containing the img link """
        
        img_str = re.search('src="([^"]+)"', img_str).group(1)
        return 'https://mr-bricolage.bg'+img_str


class JsonWriterPipeline(object):
    """ Stores the item data to the output file. """
    
    def open_spider(self, spider):
        self.file = open('scraped_items.json', 'w')
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
