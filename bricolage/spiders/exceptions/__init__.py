class BricolageScrapperError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return 'Scraper alert: %s' % self.message
