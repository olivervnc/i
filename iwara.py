#@title IwaraParser
import json
import logging
import re
import time
from urllib.parse import urljoin,quote
from html import unescape

from bs4 import BeautifulSoup
import requests
from rich.logging import RichHandler
from rich.console import Console

logging.basicConfig(format='%(message)s',datefmt='[%Y-%m-%d %H:%M:%S]',handlers=[RichHandler(rich_tracebacks=True,show_path=False,omit_repeated_times=False,console=Console(width=105))])

class IwaraParser():
  def __init__(self,host="ecchi.iwara.tv",level="WARNING",chunk_size=32*1024):
    self.host=host
    self.logger=logging.getLogger("IwaraParser")
    self.logger.setLevel(level)
    self.chunk_size=chunk_size
    self.logger.debug("Parser initiation complete")
 
  def get_video_links(self,url,headers=None):
    self.logger.debug(f"Requesting for links - {url}")
    if "iwara.tv/videos/" not in url:
      self.logger.exception(f"Not a video - {url}")
      raise RuntimeError("Not a video")
    try:
      raw=requests.get(url.replace("/videos/","/api/video/"),headers=headers).text
    except Exception as e:
      self.logger.exception(f"Http request error - {url} - {e}")
      raise e
    data=json.loads(raw)
    if data==[]:
      self.logger.info(f"No download links found - {url}")
      return []
    for i in range(len(data)):
      data[i]["uri"]=urljoin(url,data[i]["uri"])
    self.logger.info(f"Complete requesting links - {url}")
    return data
 
  def parse_video_page(self,url,headers=None):
    self.logger.info(f"Parsing video page - {url}")
    try:
      html=requests.get(url,headers=headers).text
    except Exception as e:
      self.logger.exception(f"Http request error - {url} - {e}")
      raise e
    try:
      soup=BeautifulSoup(html)
      title=unescape(soup.select("title")[0].text.split(" | Iwara")[0])
      author=unescape(soup.select("a.username")[0].text)
      private=bool(soup.select("div.well"))
      if not private:
        thumbnail=urljoin(url,soup.select("#video-player")[0].attrs["poster"])
        return dict(title=title,thumbnail=thumbnail,author=author,private=private)
      return dict(title=title,author=author,private=private)
    except Exception as e:
      self.logger.exception(f"Parse video page error - {url} - {e}")
      raise e
 
  def parse_search_page(self,url,headers=None):
    self.logger.info(f"Finding links - {url}")
    try:
      html=requests.get(url,headers=headers).text
    except Exception as e:
      self.logger.exception(f"Http request error - {url} - {e}")
      raise e
    try:
      soup=BeautifulSoup(html)
      content=soup.select("#block-system-main div.node")
      links=[]
      for item in content:
        data={}
        title=item.select(".title")[0]
        author=item.select("a.username")[0]
        data["title"]=title.text
        data["author"]=unescape(author.text)
        data["node_id"]=item.attrs['id'][5:]
        if "node-image" in item.attrs["class"]:
          data["type"]="image"
          images=[]
          for img in item.select(".field-name-field-images .field-items a"):
            images.append(urljoin(url,img.attrs["href"]))
          data["images"]=images
        if "node-video" in item.attrs["class"]:
          data["type"]="video"
          data["title"]=title.text[1:]
          thumbnail=item.select("div.field-type-video img")
          if thumbnail:
            thumbnail=urljoin(url,thumbnail[0].attrs["src"].split("?")[0]).replace("styles/thumbnail/public/","")
          else:
            thumbnail=""
          data["thumbnail"]=thumbnail
          data["link"]=urljoin(url,item.select("h3.title a")[0].attrs["href"])
        data["title"]=unescape(data["title"])
        links.append(data)
      page_max=1
      last_page_=soup.select("ul.pager li.last")
      if last_page_:
        last_page=last_page_[0]
        if "»" in last_page.text:
          page_max=int(last_page.select("a")[0].attrs["href"].split("=")[-1])+1
        else:
          page_max=int(last_page.text)
      if not content:
        self.logger.info(f"No links found - {url}")
      else: 
        self.logger.info(f"Complete parsing page - {url}")  
      return dict(max=page_max,links=links)
    except Exception as e:
      self.logger.exception(f"Html parse error - {url} - {e}")
      raise e
 
  def download(self,url,tar,headers=None,retries=3,stream=True):
    self.logger.info(f'Downloading - "{tar}" from {url}')
    error=None
    for i in range(retries):
      try:
        self.logger.debug(f'Download trial({i}) - "{tar}" from {url}')
        r=requests.get(url,stream=stream,headers=headers)
        with open(tar,"wb") as f:
          if stream:
            for i,chunk in enumerate(r.iter_content(self.chunk_size)):
              self.logger.debug(f'Downloading - "{tar}" chunk {i} - {url}')
              f.write(chunk)
          else:
            f.write(r.content)
      except Exception as e:
        error=e
        time.sleep(10)
      else:
        self.logger.info(f'Complete downloading - "{tar}" from {url}')
        return
    self.logger.exception(f"Download error - {url} - {error}")
    raise error
  
  @staticmethod
  def generate_search_link(key="",page=0,host="ecchi.iwara.tv",args=None):
    url=f"https://{host}/search?query={key}&page={page}"
    if args:
      args_=""
      for i,(key,arg) in enumerate(args.items()):
        args_+="&"+f"f%5B{i}%5D={key}:{quote(str(arg))}"
      url+=args_
    return url
