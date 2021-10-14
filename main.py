import os
import logging
import shutil
import time
from multiprocessing.pool import ThreadPool as Pool

from rich.logging import RichHandler
from rich.console import Console

from iwara import IwaraParser

parser=IwaraParser(level="CRITICAL")
generate_search_link=parser.generate_search_link
download=parser.download
parse_search_page=parser.parse_search_page
parse_video_page=parser.parse_video_page
get_video_links=parser.get_video_links

logger_level="INFO" #@param ["DEBUG","INFO","WARNING","ERROR","CRITICAL"]
stream=False #@param {type:"boolean"}

logging.basicConfig(format='%(message)s',datefmt='[%Y-%m-%d %H:%M:%S]',handlers=[RichHandler(rich_tracebacks=True,show_path=False,omit_repeated_times=False,console=Console(width=105))])
logger=logging.getLogger("Download")
logger.setLevel(logger_level)
 
def add_handler(filename,level):
  """formatter=logging.Formatter('[%(levelname)s] - %(name)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
  file_handler=logging.FileHandler(filename,mode='a')
  file_handler.setLevel(level)
  file_handler.setFormatter(formatter)"""
  file_handler=RichHandler(
      log_time_format="[%Y-%m-%d %X]",
      level=level,
      rich_tracebacks=True,
      show_path=False,
      console=Console(file=open(filename,"at"),
              force_jupyter=False)
      )
  logger.addHandler(file_handler)
 
handler_added=False
 
def v(title):
    #rstr = r"[\/\\\:\*\?\"\<\>\|\`\'"+"\\\r\\\t\\\n]"  # '/ \ : * ? " < > |'
    rstr = r"[\/\\\t]"  # '/ \ : * ? " < > |'
    new_title = re.sub(rstr, "_", title)  # 替换为下划线
    return new_title

def fake_headers():
  return {"User-Agent":UserAgent().random}
def download_thumbnail(thumbnail,headers,title,node_id,tar):
  try:
    image_content=requests.get(thumbnail,headers=headers).content
    with open(os.path.join(tar,f"{title}_{node_id}.jpg"),"wb") as f:
      f.write(image_content)
  except Exception as e:
    logger.exception(f"下载出错:{title} - {thumbnail} - {e}")

def download_single(args):
  item,sub=args
  node_id=item['node_id']
  headers=fake_headers()
  if type(item)==str:
    logger.critical(item)
  title=v(item["title"])
  if '言和' in title:
    return
  author=v(item["author"])
  #tar=os.path.join(output_dir,sub,author)
  tar=os.path.join(output_dir,author)
  os.makedirs(tar,exist_ok=True)
  if item["type"]=="image":
    if not item['images']:
       logger.warning(f'无图片:{item["title"]} 作者:{item["author"]}')
       return
    title_=title+'_'+node_id
    tmp=os.path.join("/content/tmp/iwara",sub,author,title_)
    os.system(f'rm -r "{tmp}"')
    os.makedirs(tmp,exist_ok=True)    
    if len(item["images"])>1:
      if os.path.exists(os.path.join(tar,f"{title_}.zip")):
        logger.warning(f"已存在:{title} 作者:{author}")
        return
    os.system(f'cd {tar} && rm "{title_}.zip" && rm "{title_}.jpg"')
    logger.info(f"开始下载:{title} 作者:{author}")
    start_time=time.time()
    try:
      for i,image in enumerate(item["images"]):
        try:
          image_content=requests.get(image,headers=headers).content
          with open(os.path.join(tmp,f"{i+1}.jpg"),"wb") as f:
            f.write(image_content)
        except Exception as e:
          logger.exception(f"下载出错:{image} - {e}")
      if len(os.listdir(tmp))>1:
        os.system(f'cd "{tmp}" && zip "{title_}.zip" *')
        shutil.move(os.path.join(tmp,f"{title_}.zip"),tar)
      if os.listdir(tmp):
        shutil.move(os.path.join(tmp,os.listdir(tmp)[0]),os.path.join(tar,f"{title_}.jpg"))
    except Exception as e:
      logger.exception(f"下载出错:{title} - {e}")
    shutil.rmtree(tmp)
    if time.time()<start_time+5:
      time.sleep(start_time+5-time.time())
  elif item["type"]=='video':
    tmp=os.path.join("/content/tmp/iwara",sub,author,node_id)
    os.system(f'rm -r "{tmp}"')
    os.makedirs(tmp,exist_ok=True)
    logger.info(f"开始下载:{title} 作者:{author}")
    thumbnail=item["thumbnail"]
    if thumbnail:
      download_thumbnail(thumbnail,headers,title,node_id,tar)
    else:
      """data=parse_video_page(item["link"])
      if "thumbnail" in data.keys():
        thumbnail=data["thumbnail"]
        download_thumbnail(thumbnail,headers,title,node_id,tar)
      else:"""
      logger.warning(f'未找到封面:{title} - {item["link"]}')
    try:
      urls=get_video_links(item["link"],headers=headers)
      start_time=time.time()
    except Exception as e:
      logger.exception(f"获取链接出错:{title} - {e}")
      time.sleep(5)
      return
    if not urls:
      logger.warning(f"私有视频:{title},仅下载封面")
      time.sleep(5)
      return
    for url in urls[::-1]:
      target=os.path.join(tar,f'{title}_{url["resolution"]}_{node_id}.mp4')
      if os.path.exists(target):
        logger.info(f"已存在:{title}_{url['resolution']} 作者:{author}")
        continue
      try:
        if stream:
          download(url["uri"],os.path.join(tmp,f'{title}_{url["resolution"]}_{node_id}.mp4'),stream=False,headers=headers)
          shutil.move(os.path.join(tmp,f'{title}_{url["resolution"]}_{node_id}.mp4'),target)
        else:
          download(url["uri"],target,stream=False)
      except Exception as e:
        logger.exception(f"下载出错:{title}_{url['resolution']} - {e}")
    if time.time()<start_time+5:
      time.sleep(start_time+5-time.time())
  logger.info(f"下载完成:{title}")
 
def download_page(links,sub,parallel=5):
  args=[(item,sub) for item in links]
  with Pool(parallel) as p:
    p.map(download_single,args)

import os
import json
import time

from fake_useragent import UserAgent

output_dir="/content/drive/Shareddrives/OT1/iwara011" #@param {type:"string"}
restart=False #@param {type:"boolean"}

os.makedirs(output_dir,exist_ok=True)
process_path=os.path.join(output_dir,"process.json")
process={}
 
def save_process():
  logger.info("正在保存进度")
  try:
    with open(process_path,"w") as f:
      json.dump(process,f)
    logger.info(f'进度已保存至"{process_path}"')
    #logger.info(f'进度已保存至"{process_path}" - {process}')
  except:
    logger.warning(f'进度保存出错')

def clear_output():
  os.system("clear")

if not restart: 
  try:
    with open(process_path) as f:
      process=json.load(f)
    logger.info(f"即将载入进度: {process}，请确认")
    #input()
  except Exception as e:
    logger.info("未找到进度文件，从头开始")
else:
  logger.warning("即将从头开始，按回车键继续")
  input()
  process={}
  [os.system(f"rm {os.path.join(output_dir,level+'.log')}") for level in ("DEBUG","WARNING","ERROR")]
  clear_output()

if not handler_added:
  [add_handler(os.path.join(output_dir,level+".log"),level) for level in ("DEBUG","WARNING","ERROR")]
  handler_added=True
for name,l in keys.items():
  l=[name]+l
  if name not in process.keys():
    process[name]={}
  for key in l:
    if key not in process[name].keys():
      process[name][key]=-1
    start=process[name][key]+1
    data=parse_search_page(generate_search_link(key,page=start),headers=fake_headers())
    max_page=data["max"]
    logger.info(f"下载 {key} 第 {start} / {max_page} 页")
    download_page(data["links"],name)
    clear_output()
    if start>=max_page:
      process[name][key]=max_page-1
      logger.info(f"{key} 已下载完")
      clear_output()
      save_process()
      continue
    process[name][key]=start
    save_process()
    for page in range(start+1,max_page):
      logger.info(f"下载 {key} 第 {page} / {max_page} 页")
      download_page(parse_search_page(generate_search_link(key,page=page),headers=fake_headers())["links"],name)
      process[name][key]=page
      clear_output()
      save_process()
    logger.info("暂停5秒，让服务器休息一下。。。")
    time.sleep(5)
