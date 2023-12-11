#!/bin/python3
import requests
import click
from bs4 import BeautifulSoup
from pprint import pprint
from urllib.parse import urlparse, urljoin
from anytree import Node,RenderTree
import colorama
import re

class NestedDict:


    def __init__(self):
        self.data = {}
        self.list = []
        self.templist = []
        self.tempdict = {}
        self.root = Node("URLs")

    def add_external_url(self,url):
        self.data[url] = {}

    def add_path(self,url):
        path_parse = list(filter(lambda x: x != "",urlparse(url).path.split("/")))
        baseUrl = Crawler.get_url_base(url)
        if baseUrl not in self.data.keys():
            self.data[baseUrl] = {}
        temp = self.data[baseUrl]
        if len(path_parse) == 0: return
        for key in path_parse:
            if key not in temp:
                temp[key] = {}
            temp = temp[key]

    def print_data(self):
        return self.data


    def print_data_tree_format(self):
        self.create_tree(self.data,self.root)
        for pre, _, node in RenderTree(self.root):
            print(f"{pre}{node.name}")

    def print_data_list_format(self):
        self.tempdict = self.data.copy()
        # key son las url raiz: scheme://example.com

        self.get_dirs_list(self.data.copy())
        print(f"\n{colorama.Fore.BLUE}######## URLs ########{colorama.Style.RESET_ALL}\n")
        for link in self.list:
            print(f"\t{link}")
        return

    def get_dirs_list(self,d):
        for key in d.keys():
            self.templist.append(key)
            if len(d[key]) > 0:

                self.get_dirs_list(d[key])
            # resetea el diccionario temporal
            else:
                self.list.append("/".join(self.templist))
            self.templist.pop(-1)




    def create_tree(self,dictionary,parent):
        for key, value in dictionary.items():
            node = Node(key,parent=parent)
            if isinstance(value, dict):
                self.create_tree(value,node)



class Crawler:
    def __init__(self, url, cookies={}):
        self.url = self.get_url_base(url)
        self.url_with_path = self.get_url_base(url) + urlparse(url).path
        self.cookies = cookies
        self.dict = NestedDict()

    def get_urls(self,recursive):
        '''
        retrive all URLs from the page and store them
        '''
        try:
            r = requests.get(self.url_with_path,cookies=self.cookies)
            s = BeautifulSoup(r.text, 'html.parser')

            self.dict.add_path(self.url_with_path)
            for a in s.find_all("a"): # busca todas las etiquetas a
                link = a["href"]

                if not link: continue # si el atributo href es nulo continua con el siguiente tag
                if "mailto" in link: continue
                if self.has_scheme(link): # si tiene scheme
                    self.dict.add_path(link)
                    continue

                if link[0] != "/": # ruta relativa
                    # check if link is in the same level directory or subdirectory
                    self.dict.add_path(urljoin(self.url,link))

                else: # ruta absoluta

                    self.dict.add_path(urljoin(self.url,link))

                    continue

        except requests.exceptions.MissingSchema as e:
            print(e)
        except requests.exceptions.InvalidSchema as e:
            print(e)
        except requests.exceptions.ConnectionError as e:
            print(e)
        except Exception as e:
            print(e.with_traceback())

    def get_robots(self):
        r = requests.get(urljoin(self.url,"robots.txt"))
        if r.status_code == 200:
            print(f"ALL DISALLOW PATHS IN ROBOTS.TXT\n")
            for path in re.findall(r"^Disallow:\s*(.*)",r.text,re.MULTILINE):
                print(f"{path} {Crawler.check_status(urljoin(self.url,path))}")

        else:
            print(f"{colorama.Fore.RED} [-] No se puede mostrar robots.txt, status code:{r.status_code}{colorama.Style.RESET_ALL}")

    @staticmethod
    def get_url_base(url):
        '''
        return scheme://netloc, for example http://google.com/accounts -> http://google.com
        '''
        return urlparse(url).scheme + "://" + urlparse(url).netloc

    @staticmethod
    def check_status(url):
        sc = requests.get(url).status_code
        if sc == 200:
            return f"{colorama.Fore.GREEN}-> {sc} {colorama.Style.RESET_ALL}"
        else:
            return f"{colorama.Fore.RED}-> {sc} {colorama.Style.RESET_ALL}"

    def has_scheme(self, url):
        '''
        check if link has http scheme
        '''
        if "http" in urlparse(url).scheme:
            return True
        return False

    def print_all_urls(self,m):
        '''
        print data in different formats
        '''
        if m == "json":
            pprint(self.dict.print_data())
        elif m == "tree":
            self.dict.print_data_tree_format()
        elif m == "list":
            self.dict.print_data_list_format()


@click.command(name="e")
@click.option("-c","--cookies","cookies",)
@click.option("-r","--recursive","recursive")
@click.option("-o","--output","output", help="Output file, (should be in json format exported)")
@click.option("-i","--input-file","inputfile", help="Filename of output to save.")
@click.option("-m","--mode","mode",type=click.Choice(["json","tree","list"]),default="json", show_default=True)
@click.argument('url', metavar='<url>')
def extract_urls(url,cookies,recursive,mode,output,inputfile):
    '''
    Extrae todas las urls de la <url> pasada como argumento
    '''
    c = Crawler(url=url,cookies=cookies)
    c.get_urls(recursive)
    c.print_all_urls(mode)

@click.command(name="robots")
@click.argument('url', metavar='<url>')
def robots(url):
    '''
    extract robots.txt file
    '''
    c = Crawler(url=url)
    c.get_robots()
    return

@click.group(name="main")
def main():
    '''
    Script for web crawling
    '''
    return

main.add_command(extract_urls)
main.add_command(robots)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e.with_traceback())
