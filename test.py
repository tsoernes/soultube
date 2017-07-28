from threading import current_thread
from multiprocessing import Process


class Driver():
        def __init__(self):
                self.search_results = []

        def search(self, a):
                print "search: " + current_thread().getName()
                res = "res: " + a
                self.search_results += res
                print "search result: " + str(self.search_results)

        def autodownload(self, a):
                print "autodownload: " + current_thread().getName()
                p = Process(target=self.search, args=(a,))
                p.start()
                p.join()
                print(self.search_results)

        def download(self):
                print "download: " + current_thread().getName()
                pass


print "main: " + current_thread().getName()
driver = Driver()
driver.autodownload("query")
