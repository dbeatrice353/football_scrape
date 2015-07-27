
from bs4 import BeautifulSoup
import urllib2
import time
import os

PLAYER_LISTINGS_DIR = 'player_listings'
PLAYER_PROFILES_DIR = 'player_profiles'
SCRAPED_PLAYER_INFO = 'scraped_player_info'

class FFTodayWebClient:
    def __init__(self):
        self.base_url = 'http://fftoday.com'
        self.player_listings_dir = PLAYER_LISTINGS_DIR
        self.player_profiles_dir = PLAYER_PROFILES_DIR
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
        return time.strftime('%Y-%m-%d %H:%M:%S') + '\t' + str(exception.reason) + '\t' + url + '\n'

    def _log_error(self,url,e):
        with open(self.error_log_file,'a') as f:
            error_string = self._make_error_string(url,e)
            f.write(error_string)

    def _save_page(self,page,url,directory):
        output_file = url.replace('/','_') + '.html'
        output_path = os.path.join(directory,output_file)
        with open(output_path,'w') as f:
            f.write(page)

    def _download(self, request,destination_directory):
        url = request.get_full_url()
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            self._log_error(url,e)
        except urllib2.URLError as e:
            self._log_error(url,e)
        else:
            page = response.read()
            self._save_page(page,url,destination_directory)


    def download_player_listings(self,delay=5,monitor=False):
        # Download the pages that list the player's names, and hyperlinks to their profiles.
        # The player listing pages are by position.
        positions = ['QB','RB','WR','TE','K','DL','LB','DB']
        for position in positions:
            url = self._make_player_listing_url(position)
            request = self._make_request(url)
            self._download(request,self.player_listings_dir)
            if monitor:
                print url
            time.sleep(delay)

    def download_player_profiles(self,delay=5,monitor=False):
        scraper = Scraper()
        names_and_urls = scraper.scrape_player_listings()
        for record in names_and_urls:
            url = self.base_url + record[1]
            request = self._make_request(url)
            self._download(request,self.player_profiles_dir)
            if monitor:
                print url
            time.sleep(delay)

class Scraper:
    def __init__(self):
        self.player_listings_dir = PLAYER_LISTINGS_DIR
        self.player_profiles_dir = PLAYER_PROFILES_DIR
        self.scraped_player_info_dir = SCRAPED_PLAYER_INFO
        self.scraped_player_info_file = 'scraped_player_info.dat'
        self.scraped_season_stats_file = 'scraped_season_stats.dat'
        self.scraped_gamelog_stats_file = 'scraped_gamelog_stats.dat'

    def _check_if_player_listings_dir_exists(self):
        if not os.path.exists(self.player_listings_dir):
            raise Exception("The player listings directiory does not exit.")

    def _check_if_player_profiles_dir_exists(self):
        if not os.path.exists(self.player_profiles_dir):
            raise Exception("The player profiles directiory does not exit.")

    def _check_if_scraped_player_info_dir_exists(self):
        if not os.path.exists(self.scraped_player_info_dir):
            os.mkdir(self.scraped_player_info_dir)
        # clear the file.

    def _clear_output_files(self):
        for file in [self.scraped_player_info_file, self.scraped_season_stats_file, self.scraped_gamelog_stats_file]:
            path = os.path.join(self.scraped_player_info_dir,file)
            f = open(path,'w')
            f.close()

    def _extract_name(self,string):
        string = string.replace(',','')
        parts = string.split(' ')
        return parts[1] + ' ' + parts[0]

    def _parse_player_listings(self,page):
        soup = BeautifulSoup(page,"lxml")
        tables = soup.find_all('table')
        table = tables[7] # the goods are in table 7
        a_tags = table.find_all('a')
        records = [[self._extract_name(a.text), a['href']] for a in a_tags]
        return records

    def _get_position_from_string(self,string):
        # get the football position from the filename/url
        string = string.replace('.html','')
        parts = string.split('=')
        return parts[-1]

    def _add_position(self,records,position):
        return [record + [position] for record in records]

    def scrape_player_listings(self):
        self._check_if_player_listings_dir_exists()
        files = os.listdir(self.player_listings_dir)
        player_listings = []
        for file in files:
            position = self._get_position_from_string(file)
            path = os.path.join(self.player_listings_dir,file)
            with open(path,'r') as f:
                page = f.read()
            records = self._parse_player_listings(page)
            records = self._add_position(records,position)
            player_listings += records
        return player_listings

    def scrape_player_information(self,soup,player_id):
        # '\N' is the null-character for MySQL
        null_character = '\N'
        player_record = {'first_name':null_character,
                         'last_name':null_character,
                         'current_position':null_character,
                         'current_team':null_character,
                         'DOB':null_character,
                         'age':null_character,
                         'height':null_character,
                         'weight':null_character,
                         'draft':null_character,
                         'college':null_character,
                         'id':unicode(player_id)}
        # some player info comes from in the title tag
        try:
            position_name_team = soup.title.text.replace('- FF Today','') # position/name/team
            parts = position_name_team.split(' ')
            player_record['current_position'] = parts[0]
            player_record['first_name'] = parts[1]
            player_record['last_name'] = parts[2]
            player_record['current_team'] = position_name_team.split(',')[-1]
        except IndexError as e:
            print position_name_team
            raise e
        else:
            pass
        # Other player info comes from a poorly structured table further down the page.
        tables = soup.find_all('table')
        player_info = unicode(tables[7].td)
        # get rid of some pesky html
        for each in ['<br/>','<td>','</td>','<td class="bodycontent"><strong>','</strong>']:
            player_info = player_info.replace(each,'')
        player_info = player_info.split('<strong>')
        # include any fields that are available
        for each in player_info:
            field = each.split(':')
            if 'DOB' in field[0]:
                player_record['DOB'] = field[1]
            if 'Age' in field[0]:
                player_record['age'] = field[1]
            if 'Ht' in field[0]:
                player_record['height'] = field[1]
            if 'Wt' in field[0]:
                player_record['weight'] = field[1]
            if 'College' in field[0]:
                player_record['college'] = field[1]
            if 'Draft' in field[0]:
                player_record['draft'] = field[1]
        # save the record
        return player_record

    def find_lowest_element_containing_string(self,soup,element_type,string):
        # recursivly find the lowest table that contains the string.
        elements = soup.find_all(element_type)
        for element in elements:
            if string in element.text:
                if len(element.find_all(element_type)) > 0:
                    return self.find_lowest_element_containing_string(element,element_type,string)
                else:
                    return element
        return None

    def scrape_season_stats(self,soup,player_id):
        player_id = unicode(player_id)
        # find the season stats table
        identifier_string = "Team"
        element_type = 'table'
        table = self.find_lowest_element_containing_string(soup,element_type,identifier_string)
        if table:
            season_stat_records = []
            rows = table.find_all('tr')
            # get the headers
            headers_row = rows[1]
            tds = headers_row.find_all('td')
            headers = [td.text for td in tds]
            # get the data
            for row in rows[2:]:
                tds = row.find_all('td')
                stat_season = tds[0].text
                stat_team = tds[1].text
                for i in range(2,len(headers)): # skip season and team
                    stat_type = headers[i]
                    stat_value = tds[i].text
                    record = [player_id,stat_season,stat_team,stat_type,stat_value]
                    season_stat_records.append(record)
            return season_stat_records

    def scrape_gamelog_stats(self,soup,year,player_id):
        player_id = unicode(player_id)
        identifier_string = year + ' Gamelog Stats'
        element_type = 'table'
        # this line finds the table that directly preceeds the one we want
        table = self.find_lowest_element_containing_string(soup,element_type,identifier_string)
        tables = soup.find_all('table')
        index = tables.index(table)
        # the gamelog table...
        gl_table = tables[index + 1]
        gamelog_records = []
        rows = gl_table.find_all('tr')
        # get the headers
        headers_row = rows[2]
        tds = headers_row.find_all('td')
        headers = [td.text for td in tds]
        # get the data
        for row in rows[3:]:
            tds = row.find_all('td')
            stat_week = tds[0].text
            stat_opponent = tds[1].text
            stat_result = tds[2].text
            for i in range(3,len(headers)): # skip season and team
                stat_type = headers[i]
                stat_value = tds[i].text
                record = [player_id,stat_week,stat_opponent,stat_type,stat_value]
                gamelog_records.append(record)
        return gamelog_records


    def scrape_player_profiles(self):
        self._check_if_player_profiles_dir_exists()
        self._check_if_scraped_player_info_dir_exists()
        self._clear_output_files()
        files = os.listdir(self.player_profiles_dir)
        player_records = []
        season_stats_records = []
        gamelog_stats_records = []
        i = 0
        for file in files:
            # provide some output so we know its running
            i += 1
            if i % 50 == 0:
                print i
            player_id = i
            # read the file
            path = os.path.join(self.player_profiles_dir,file)
            with open(path,'r') as f:
                page = f.read().decode("utf8",errors='ignore')
            # make the soup
            soup = BeautifulSoup(page,"lxml")
            # scrape
            player_record = self.scrape_player_information(soup,player_id)
            player_records.append(player_record)
            if 'Season Stats' in page:
                season_stats = self.scrape_season_stats(soup,player_id)
                season_stats_records += season_stats
            for year in ['2012','2013','2014','2015']:
                if year + ' Gamelog Stats' in page:
                    gamelog_stats = self.scrape_gamelog_stats(soup,year,player_id)
                    gamelog_stats_records += gamelog_stats

        self.save_season_stats(season_stats_records)
        self.save_player_records(player_records)
        self.save_gamelog_stats(gamelog_stats_records)

    def save_player_records(self,player_records):
        output_path = os.path.join(self.scraped_player_info_dir,self.scraped_player_info_file)
        with open(output_path,'a') as f:
            for record in player_records:
                output_string = '\t'.join(record.values())+'\n'
                f.write(output_string.encode('utf-8'))

    def save_season_stats(self,season_stats):
        output_path = os.path.join(self.scraped_player_info_dir,self.scraped_season_stats_file)
        with open(output_path,'a') as f:
            for record in season_stats:
                output_string = '\t'.join(record)+'\n'
                f.write(output_string.encode('utf-8'))

    def save_gamelog_stats(self,gamelog_stats):
        output_path = os.path.join(self.scraped_player_info_dir,self.scraped_gamelog_stats_file)
        with open(output_path,'a') as f:
            for record in gamelog_stats:
                output_string = '\t'.join(record)+'\n'
                f.write(output_string.encode('utf-8'))


if __name__ == "__main__":
    #client = FFTodayWebClient()
    #client.download_player_listings(delay=5,monitor=False)
    #client.download_player_profiles(delay=3,monitor=True)
    scraper = Scraper()
    data = scraper.scrape_player_profiles()
