import scrapy
import re
import logging
from urlparse import urlparse
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor
from scrapy.linkextractors import LinkExtractor
from scrapy import signals
from scrapy.http import Request
from scrapy.utils.httpobj import urlparse_cached


logger = logging.getLogger(__name__)


class LinkItem(scrapy.Item):
    """
    Basic object for link extraction
    """
    url = scrapy.Field()


class KeywordMiddleware(object):
    """
    Keyword spider middleware. Workis like offsite middleware + allows to
    visit sites with the specific keyword in it (e.g. corporate name)
    """

    def __init__(self, stats):
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler.stats)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        return o

    def process_spider_output(self, response, result, spider):
        for x in result:
            if isinstance(x, Request):
                if x.dont_filter or self.should_follow(x, spider):
                    yield x
                else:
                    domain = urlparse_cached(x).hostname
                    if domain and domain not in self.domains_seen:
                        self.domains_seen.add(domain)
                        logger.debug("Filtered offsite-x request to %(domain)r: %(request)s",
                                     {'domain': domain, 'request': x}, extra={'spider': spider})
                        self.stats.inc_value('offsite/domains', spider=spider)
                    self.stats.inc_value('offsite/filtered', spider=spider)
            else:
                yield x

    def should_follow(self, request, spider):
        regex = self.host_regex
        kws = self.host_kw
        # hostname can be None for wrong urls (like javascript links)
        host = urlparse_cached(request).hostname or ''
        regex_match = bool(regex.search(host))
        if regex_match:
            return True
        for kw in kws:
            if kw in host:
                return True
        return False

    def get_host_regex(self, spider):
        """Override this method to implement a different offsite policy"""
        allowed_domains = getattr(spider, 'allowed_domains', None)
        if not allowed_domains:
            return re.compile('') # allow all by default
        regex = r'^(.*\.)?(%s)$' % '|'.join(re.escape(d) for d in allowed_domains if d is not None)
        return re.compile(regex)

    def get_host_kw(self, spider):
        allowed_keywords = getattr(spider, 'allowed_kw', None)
        if allowed_keywords is None:
            return []
        return allowed_keywords

    def spider_opened(self, spider):
        self.host_regex = self.get_host_regex(spider)
        self.host_kw = self.get_host_kw(spider)
        self.domains_seen = set()


class DuplicatesPipeline(object):
    """
    Pipeline for removing duplicate url items
    """

    def __init__(self):
        self.url_seen = set()

    def process_item(self, item, spider):
        if item['url'] in self.url_seen:
            raise scrapy.exceptions.DropItem("Duplicate item found: %s" % item)
        else:
            self.url_seen.add(item['url'])
            return item


class LinkSpider(CrawlSpider):
    name = 'link'

    blocked = ['facebook', 'twitter', 'youtube', 'google', 'linkedin', 'youtu.be', 'google.', 'bbc.', 'gov.',
               'reddit', 'instagram', 'yahoo', 'snachat', 'stackoverflow', 'sky.com', 'digg.com', 'amazon.',
               'adobe.']

    # Override this
    rules = (
        Rule(LxmlLinkExtractor(allow=(), deny=(), ), callback='parse_obj', follow=False),
    )

    # In case you want to modify custom_settings and preserve keyword middleware
    spider_settings = {
        'SPIDER_MIDDLEWARES': {
            'scrapper_base.KeywordMiddleware': 543,
            'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': None
        }
    }

    custom_settings = {
        'SPIDER_MIDDLEWARES': {
            'scrapper_base.KeywordMiddleware': 543,
            'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': None
        },
        'ITEM_PIPELINES': {
            # Use if want to prevent duplicates, otherwise useful for frequency analysis
            #'scrapper_base.DuplicatesPipeline': 10,
        }
    }

    def shoud_follow_link(self, link, response):
        return True

    def parse_obj(self, response):
        links_visit = set()
        links = set()
        for link in LxmlLinkExtractor(allow=(), deny=()).extract_links(response):
            o = urlparse(link.url)
            domain = o.hostname

            block_this = False
            for b in self.blocked:
                if b in domain:
                    block_this = True
                    break

            if block_this:
                continue

            links.add(domain)

            # Another filter if desired
            #logger.debug("--link %s" % link.url)
            if self.shoud_follow_link(link.url, response):
                links_visit.add(link.url)

        for d in list(links):
            item = LinkItem()
            item['url'] = d
            yield item

        for d in list(links_visit):
            yield Request(d)



    # def parse(self, response):
    #     for sel in response.xpath('//tr/td/a'):
    #         item = LinkItem()
    #         item['name'] = sel.xpath('text()').extract()
    #         item['link'] = sel.xpath('@href').extract()
    #
    #         yield item


