#!/bin/python3
import io

import requests
import click
from bs4 import BeautifulSoup
from pprint import pprint
from urllib.parse import urlparse, urljoin
from anytree import Node,RenderTree
import colorama
import re
import json

from click import Context, HelpFormatter


class NestedDict:

    
    def __init__(self):
        print(f"{colorama.Fore.GREEN}")
        print("              _      _____                    _           ")
        print("             | |    / ____|                  | |          ") 
        print("__      _____| |__ | |     _ __ __ ___      _| | ___ _ __ ") 
        print("\ \ /\ / / _ \ '_ \| |    | '__/ _` \ \ /\ / / |/ _ \ '__|")
        print(" \ V  V /  __/ |_) | |____| | | (_| |\ V  V /| |  __/ |   ") 
        print("  \_/\_/ \___|_.__/ \_____|_|  \__,_| \_/\_/ |_|\___|_|   ")
          
        print(f"{colorama.Style.RESET_ALL}")

        self.data = {}
        self.list = []
        self.templist = []
        self.tempdict = {}
        self.root = Node("URLs")

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

    def print_data_json_format(self):
        pprint(self.data)


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
            print(f"{link}")

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
    def __init__(self, url, cookies="", headers={}, proxies={}, robots=False, scope=None):
        if not urlparse(url).scheme:
            print("[-] Please, Specify a scheme for the URL, ex: http:// or https://")
            exit(1)
        self.url = self.get_url_base(url)
        #self.get_redirected_url(self.url)
        self.url_with_path = self.get_url_base(self.url) + urlparse(url).path
        self.scope = scope
        self.cookies = {}
        if cookies is not None:
            for cookie in cookies.split(","):
                self.cookies[cookie.split("=")[0]] = cookie.split("=")[1]
        self.headers = headers
        self.proxies = proxies
        self.robots = robots
        self.dict = NestedDict()


    def get_urls(self, external):
        '''
        retrive all URLs from the page and store them
        '''
        try:

            r = requests.get(self.url_with_path,headers=self.headers, cookies=self.cookies, proxies=self.proxies)
            s = BeautifulSoup(r.text, 'html.parser')

            is_in_scope = False

            self.dict.add_path(self.url_with_path)
            if self.robots:
                for line in self.get_robots():
                   self.dict.add_path(urljoin(self.url,line))

            for a in s.find_all("a"): # busca todas las etiquetas a
                link = a["href"]



                if not link: continue # si el atributo href es nulo continua con el siguiente tag
                if "mailto" in urlparse(link).scheme: continue

                if self.scope is not None:
                    file_scope = open(self.scope, "r")
                    urls = [x[:-1] for x in file_scope.readlines()]
                    for url in urls:
                        if url in self.url_with_path:  # is in scope

                            print(url)
                            is_in_scope = True
                            break
                    file_scope.close()

                    if is_in_scope:
                        is_in_scope = False
                    else:
                        continue

                if self.has_scheme(link):# if has scheme
                    self.dict.add_path(link)
                    continue
                elif link[0] != "/":  # if path relative
                    self.dict.add_path(urljoin(self.url_with_path,link))

                else:  # if absolute path
                    self.dict.add_path(urljoin(self.url,link))

        except requests.exceptions.MissingSchema as e:
            print(e)
        except requests.exceptions.InvalidSchema as e:
            print(e)
        except requests.exceptions.ConnectionError as e:
            print(e)
        except Exception as e:
            print(e)
        finally:
            pass

    def get_robots(self):
        r = requests.get(urljoin(self.url,"robots.txt"))
        paths = []
        if r.status_code == 200:
            print(f"ALL DISALLOW PATHS IN ROBOTS.TXT\n")
            for path in re.findall(r"^Disallow:\s*(.*)",r.text,re.MULTILINE):
                paths.append(path)
                #print(f"{urljoin(self.url,path)}")
            return paths
        else:
            print(f"{colorama.Fore.RED} [-] No se puede mostrar robots.txt, status code:{r.status_code}{colorama.Style.RESET_ALL}")

    @staticmethod
    def get_url_base(url):
        '''
        return scheme://netloc, for example http://google.com/accounts -> http://google.com
        '''

        if not urlparse(url).scheme.startswith("http"):
            return "http://" + urlparse(url).netloc

        return urlparse(url).scheme + "://" + urlparse(url).netloc

    @staticmethod
    def get_sc(url):
        '''
        return status code
        '''
        try:
            sc = requests.get(url).status_code
            return sc
        except Exception as e:
            return False

    def has_scheme(self, url):
        '''
        check if link has http scheme
        '''
        if "http" in urlparse(url).scheme:
            return True
        return False

    def get_redirected_url(self, url):
        '''
        Return de final redirected url
        '''
        response = requests.get(url=url, allow_redirects=False)

        if response.status_code in [301,302]:
            location = response.headers["Location"].replace("http://","https://")

        else:
            return url
    def export_data_json_format(self, name):
        try:
            with open(name,"w") as f:
                f.write(str(json.dumps(self.dict.data)))

        except Exception as e:
            print(f"{colorama.Fore.RED}[-] There was an error saving the file {name}.{colorama.Style.RESET_ALL}")

    def export_data_list_format(self, name):
        try:
            print(self.dict.list)
            with open(name,"w") as f:
                for line in self.dict.list:
                    f.write(f"{line}\n")

        except Exception as e:
            print(f"{colorama.Fore.RED}[-] There was an error saving the file {name}.{colorama.Style.RESET_ALL}")

    def export_data_tree_format(self, name):
        pass

    def print_json_format(self):
        '''
        print data in different formats
        '''

        self.dict.print_data_json_format()

    def print_list_format(self):
        self.dict.print_data_list_format()

    def print_tree_format(self):
        self.dict.print_data_tree_format()


class FormatHelp(click.Command):
    def format_help(self, ctx: Context, formatter: HelpFormatter):
        self.format_usage(ctx,formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        #click.echo("OUTPUT")
        #click.echo("SHOW")
        self.format_epilog(ctx,formatter)

    def format_options(self, ctx: Context, formatter: HelpFormatter) -> None:
        """Writes all the options into the formatter if they exist."""
        target_options = [
            ("  -u <url>:", "Target"),
            ("  -b <cookies>:", "'cookie1=value1,cookie2=text2'"),
            #("  -r:", "Recursive"),
            ("  --robots:", "Include robots"),
            ("  -s <filename>:", "Only crawl the scope sites in the filename"),
            #("  -e:", "Show external sites"),
        ]
        formatter.write_heading("\nTARGET AND SCOPE")
        formatter.write_dl(target_options)
        show_options = [
            ("  -sj/-sl/-st:", "Show data in different formats -> JSON, list or tree"),
        ]
        formatter.write_heading("\nSHOW")
        formatter.write_dl(show_options)
        output_options = [
            ("  -oj/-ol/-ot <filename>:", "Export data in different formats -> JSON, list or tree"),
        ]
        formatter.write_heading("\nOUTPUT")
        formatter.write_dl(output_options)


@click.command(cls=FormatHelp, epilog="ej: webCrawler.py -u https://google.com")
@click.option("-b", "--cookies", "cookies")
@click.option("-u", "--url", "url", type=str, required=True, metavar="<url>")
@click.option("-r", "--recursive", "recursive")
@click.option("-i", "--input-file", "inputfile")
@click.option("-s", "scope")
@click.option("-x", "extra", is_flag=True, help="Extract extra data like mails, comments, etc.")
@click.option("--robots", "robots", is_flag=True, help="Include the robots.txt file")
@click.option("-oj", "ojson", help="Export the data in JSON format", metavar="<filename>")
@click.option("-ol", "olist", help="Export the data in LIST format", metavar="<filename>")
@click.option("-ot", "otree", help="Export the data in TREE format", metavar="<filename>")
@click.option("-sj", "--show-json", "sjson", help="Show the data in JSON format", is_flag=True)
@click.option("-sl", "--show-list", "slist", help="Show the data in LIST format", is_flag=True)
@click.option("-st", "--show-tree", "stree", help="Show the data in TREE format", is_flag=True)
@click.option("-e", "--external", "external", is_flag=True)
def main(url, external, cookies, recursive, inputfile, ojson, olist, otree, sjson,slist, stree, scope, robots, extra):
    '''
    Script for web crawling
    '''


    output_list = True if len(list(filter(lambda x: True if x is not None else False,[ojson, olist, otree]))) <= 1 else False
    show_list = True if len(list(filter(lambda x: True if x else False,[sjson, slist, stree]))) <= 1 else False

    c = Crawler(url=url, cookies=cookies, robots=robots, scope=scope)
    c.get_urls(external=external)


    if show_list:
        if sjson:
            c.print_json_format()
        elif stree:
            c.print_tree_format()
        else:
            c.print_list_format()
    else:
        print("[-] Error, you should provide just one format to show the data")

    if output_list:
        if ojson is not None:
            c.export_data_json_format(ojson)
        elif olist is not None:
            c.export_data_list_format(olist)
        elif otree is not None:
            c.export_data_tree_format(otree)
    else:
        print("[-] Error, you should provide just one format save the data in the file")

    return


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
