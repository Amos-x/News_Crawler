# -*- coding: utf-8 -*-
import json
import scrapy
import datetime
from scrapy import Selector
from news.items import AllItem
import requests

class CnbcspiderSpider(scrapy.Spider):
    name = 'cnbcSpider'

    def start_requests(self):
        print('start crawking cnbc...')
        keywords = ['dollar', 'lending rates', 'bonds', 'cpooer']
        param = 'CNBC.com,The Reformed Broker,Buzzfeed,Estimize,Curbed,Polygon,Racked,Eater,SB Nation,Vox,The Verge,Recode,Breakingviews,NBC News,The Today Show,Fiscal Times,The New York Times,Financial Times,USA Today'
        for keyword in keywords:
            url = ('http://search.cnbc.com/rs/search/view.html?partnerId=2000&keywords='
                   + keyword + '&sort=date&source='+param+'&pubtime=24&pubfreq=h&page=1')
            yield scrapy.Request(url,callback=self.next_parse,dont_filter=True,meta={'goal':keyword,'page':1})

    def next_parse(self,response):
        searchResultCards = response.xpath('//div[@class="SearchResultCard"]')
        for result in searchResultCards:
            try:
                mLink = result.xpath('./h3/a/@href').extract_first()
                if 'video' in mLink:
                    continue
                item = AllItem()
                item['url'] = mLink
                item['title'] = result.xpath('./h3//text()').extract_first()
                item['time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                item['abstract'] = result.xpath('./p//text()').extract_first()
                item['classify'] = response.meta['goal']
                item['msite'] = 'cnbc'
                item['display'] = '1'
                item['source'] = result.css('span.source::text').extract_first()
                item['home_img_url'] = None
                yield scrapy.Request(mLink, callback=self.parse, meta={'item':item})
            except Exception as e:
                print(e)
                print('CNBC，Homepage Error')

        #翻页
        if searchResultCards:
            url = response.url[0:-1] + str(response.meta['page']+1)
            yield scrapy.Request(url,callback=self.next_parse,dont_filter=True,meta={'goal':response.meta['goal'],'page':response.meta['page']+1})

    def parse(self, response):
        try:
            item = response.meta['item']
            content_img_urls = response.xpath('//div[@id="article_body"]//img/@src').extract()
            item['content_img_urls'] = (content_img_urls if content_img_urls else None)
            # 获取表格数据
            tableList = response.xpath('//div[@id="article_body"]//table')
            if len(tableList) > 0:  #判断是否需要表格
                reqList = []
                trDataList = response.xpath('//tbody/tr/@data-table-chart-symbol').extract()
                for i in trDataList:
                    flag = 0
                    for j in reqList:
                        if i == j:
                            flag = 1
                            break
                    if flag == 0:
                        reqList.append(i)
                tempUrl = "http://quote.cnbc.com/quote-html-webservice/quote.htm?partnerId=2&requestMethod=quick&exthrs=1&noform=1&fund=1&output=jsonp&symbols="
                for i in reqList:
                    tempUrl += i
                    if i != reqList[-1]:
                        tempUrl += '|'
                tempUrl += "&callback=quoteHandler1"
                res = requests.get(tempUrl)
                results = json.loads(res.text[14:-1])['QuickQuoteResult']['QuickQuote']

                item['content'] = ''.join(self._parse_text(response, results))
            else:
                item['content'] = ''.join(self._parse_text(response=response))
            yield item
        except:
            print('CNBC,Content Error')

    def _parse_text(self,response,results=None):
        """解析正文"""
        try:
            mContent = []
            contentList = response.xpath(
                '//div[@id="article_deck"]//h4[@class="subtitle"] | //div[@id="article_deck"]//p | //div[@id="article_body"]//p | //div[@id="article_body"]//table | //div[@id="article_body"]//h4[@class="subtitle"] | //div[@id="article_body"]//img').extract()
            for i in contentList:
                if i[1] == 'h':
                    try:
                        mContent.append("<h4>" + Selector(text=i).xpath('//text()').extract()[0] + "</h4>")
                    except Exception as e:
                        print(e,"h")
                elif i[1] == 'p':
                    try:
                        strTemp = '<p>'
                        pStr = Selector(text=i).xpath('//text()').extract()
                        for i in pStr:
                            if i != '*':
                                strTemp += i
                            else:
                                break
                        mContent.append(strTemp + "</p>")
                    except Exception as e:
                        print(e,"p")
                elif i[1] == 't':
                    try:
                        strTemp = '<table><thead><tr>'
                        strTemp += '<th>Symbol</th><th>Price</th><th>Change</th><th>%Change</th></tr></thead><tbody>'
                        trList = Selector(text=i).xpath('//tbody/tr/td[1]//text()').extract()
                        for j in trList:
                            strTemp += '<tr><td>' + j + '</td>'
                            for k in results:
                                if j == k['shortName']:
                                    strTemp += '<td>' + k['last'] + '</td>'
                                    strTemp += '<td>' + k['change'] + '</td>'
                                    strTemp += '<td>' + k['change_pct'] + '</td>'
                                    break
                            strTemp += '</tr>'
                        strTemp += '</tbody></table>'
                        mContent.append(strTemp)
                    except Exception as e:
                        print(e,"t")

                elif i[1] == 'i':
                    try:
                        imgSrc = Selector(text=i).xpath('//img/@src').extract()[0]
                        mContent.append('<p><img src=' + imgSrc + '></p>')
                    except Exception as e:
                        print(e,"i")
            return mContent
        except Exception as e:
            print('CNBC,content function Error')





