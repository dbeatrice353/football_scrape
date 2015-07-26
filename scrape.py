
from bs4 import BeautifulSoup
import urllib2
import time
import os

class FFTodayWebClient:
    def __init__(self):
        self.base_url = 'http://fftoday.com'
        self.player_listings_dir = 'player_listings'
        self.player_profiles_dir = 'player_profiles'
        self.error_log_file = 'error_log.txt'
        self._make_directories()

    def _make_directories(self):
        for path in [self.player_listings_dir,self.player_profiles_dir]:
            if not os.path.exists(path):
                os.mkdir(path)

    def _make_request(self,url):
        headers = { 'User-Agent' : 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)' }
        data = ''
        return urllib2.Request(url, data, headers)

    def _make_player_listing_url(self,position):
        return self.base_url + '/stats/players?Pos=' + position

    def _make_error_string(self,url,exception):
        return time.strftime('%Y-%m-%d %H:%M:%S') + '\t' + exception.reason + '\t' + url + '\n'

    def _log_error(self,url,e):
        with open(self.error_log_file,'a') as f:
            error_string = self._make_error_string(url,e)
            f.write(error_string)

    def _save_page(self,page,url):
        output_file = url.replace('/','_') + '.html'
        output_path = os.path.join(self.player_listings_dir,output_file)
        with open(output_path,'w') as f:
            f.write(page)

    def _download(self, request):
        url = request.get_full_url()
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            self._log_error(url,e)
        except urllib2.URLError as e:
            self._log_error(url,e)
        else:
            page = response.read()
            self._save_page(page,url)


    def download_player_listings(self,delay=5,monitor=False):
        # Download the pages that list the player's names, and hyperlinks to their profiles.
        # The player listing pages are by position.
        positions = ['QB','RB','WR','TE','K','DL','LB','DB']
        for position in positions:
            url = self._make_player_listing_url(position)
            request = self._make_request(url)
            self._download(request)
            if monitor:
                print url
            time.sleep(delay)

if __name__ == "__main__":
    client = FFTodayWebClient()
    client.download_player_listings(delay=5,monitor=True)
