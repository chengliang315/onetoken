"""
使用方法

git clone https://github.com/1token-trade/onetoken
cd onetoken
python examples/get_historical_quote.py
"""
import gzip
import json
import logging
import os

import requests
import yaml
import time
from urllib.request import urlopen, Request
import logging
import pandas as pd

# 把下面的OT Key换成自己的OT Key, 申请方法如下
# https://1token.trade/account/apis
# https://1token.trade/dataservice
OT_KEY = 'gkRrDdvH-5K7jO54c-BO0cGq3m-iOsoA97I'


def get_contracts(date, quote_type):
    url = 'https://hist-quote.1tokentrade.cn/{}/contracts?date={}'.format(quote_type, date)
    print('get contracts: ', url)
    r = requests.get(url, timeout=5)
    if r.status_code != 200:
        print('fail get contracts', r.status_code, r.text)
    print('----------available contracts------------')
    print('total size', len(r.json()))
    print('first 10 contracts', r.json()[:10])


def download(url, file_path):
    print('downloading', url)
    r = requests.get(url, headers={'ot-key': ot_key}, stream=True)
    if r.status_code != 200:
        print('fail get historical data', r.status_code, r.text)
        print('failed ot-key', ot_key[:5], ot_key[-5:], len(ot_key))
        return
    print('quota-remaining:', r.headers.get('ot-quota-remaining'),
          'quota-consumption:', r.headers.get('ot-quota-consumption'))
    block_size = 300 * 1024
    total = 0
    with open(file_path, 'wb') as f:
        for data in r.iter_content(block_size):
            f.write(data)
            total += len(data) / 1024
            print('downloaded {}kb'.format(round(total)))


def download_simple_ticks(contract, date, file_path):
    url = 'https://hist-quote.1tokentrade.cn/ticks/simple?date={}&contract={}'.format(date, contract)
    download(url, file_path)


def download_full_ticks(contract, date, file_path):
    url = 'https://hist-quote.1tokentrade.cn/ticks/full?date={}&contract={}'.format(date, contract)
    download(url, file_path)


def download_zhubis(contract, date, file_path):
    url = 'https://hist-quote.1tokentrade.cn/trades?date={}&contract={}'.format(date, contract)
    download(url, file_path)


def download_and_print_candles(contract, since, until, duration):
    # support format: json & csv, default json
    url = 'https://hist-quote.1tokentrade.cn/candles?since={}&until={}&contract={}&duration={}&format=json'.format(
        since, until, contract, duration)
    print('downloading', url)
    resp = requests.get(url, headers={'ot-key': ot_key})
    if resp.status_code != 200:
        print('fail get candles', resp.status_code, resp.text)
        return
    r = resp.json()
    total = len(r)
    print('total', total, 'data')
    print('quota-remaining:', resp.headers.get('ot-quota-remaining'),
          'quota-consumption:', resp.headers.get('ot-quota-consumption'))
    print('--------this script will print all  data--------------')
    for i, candle in enumerate(r):
        print('{}/{}'.format(i, total), json.dumps(candle))


def unzip_and_read(path):
    data = open(path, 'rb').read()
    r = gzip.decompress(data).decode()
    total = len(r.splitlines())
    csvpath = path.replace('.gz', '.csv')
    open(csvpath, 'w').write(r)
    print('total', total, 'data')
    # print('--------this script will print all data--------------')
    for i, line in enumerate(r.splitlines()):
        try:
            # print('{}/{}'.format(i, total), line)
            pass
        except:
            pass


def load_otkey():
    if OT_KEY != 'aaaaa-bbbbb-ccccc-ddddd':
        return OT_KEY
    path = os.path.expanduser('~/.onetoken/config.yml')
    if os.path.isfile(path):
        try:
            js = yaml.load(open(path).read())
            if 'ot_key' in js:
                return js['ot_key']
            return js['api_key']
        except:
            logging.exception('failed load otkey')
    return input('input your otkey: ')

def _http_get_request(date):
    headers = {
        'User-Agent': 'PostmanRuntime/7.28.4',
        'Content-type': 'application/json; charset=utf-8',
    }
    request = Request(url='https://hist-quote.1tokentrade.cn/trades/contracts?date='+date, headers=headers,unverifiable=True)
    while True:
        try:
            #本地访问
            content = urlopen(request, timeout=30).read()
            #服务器访问（ssl验证）
            # content = urlopen(url,context=ssl._create_unverified_context(), timeout=30).read()
            # print(type(list(content)))
            # print(list(content))
            break
        except Exception as e:
            print("(get)Http Error try to resend in one second error: {} \n url:{}".format(e,url))
            time.sleep(1)
    content = content.decode('utf-8')
    json_data = json.loads(content)
    return [x for x in json_data if 'deribit' in x and 'btc' in x and 'call' in x]

def get_final_data(date,price_close,data,price_limit,day=14):
    global df_options
    l=[]
    highest_price=0
    if len(data) > 0:
        for i in data:
            dataStr=i.split(".")
            potion_price=float(dataStr[-2])
            potion_date=dataStr[-3]
            if potion_price <= price_limit and (pd.to_datetime(potion_date)-pd.to_datetime(date)).days<= day:
                df_options=df_options.append(pd.Series([date,price_close,i,potion_date,potion_price],index=df_options.columns),ignore_index=True)
                if potion_price>highest_price:
                    highest_price=potion_price
    return highest_price

def write_deribit_options_to_csv():
    df_btc_price = pd.read_csv('btc_20220226.csv', parse_dates=['date']) 
    start_time='2021-02-01'
    end_time='2022-02-28'
    date_range=14
    yesterday_price_limit=0
    # df_options=df_options.append(pd.Series([1,1,1,1,1],index=df_options.columns),ignore_index=True)  
    # print(df_options)
    # try:
    for index,row in df_btc_price.iterrows():
        if row['date']<=pd.to_datetime(end_time) and row['date']>=pd.to_datetime(start_time):
            print(str(row['date']))
            result=_http_get_request(str(row['date'])[:10])
            default_price_limit=float(row['btc'])*1.3
            yesterday_price_limit=get_final_data(str(row['date']),float(row['btc']),result,default_price_limit if default_price_limit >= yesterday_price_limit else yesterday_price_limit ,date_range)
    # # except Exception as e:
    # #     print(e)
    # # finally:
    df_options.to_csv('deribit_options.csv')  
    print(df_options)
def download_deribit_data():
    df_deribit_list = pd.read_csv('deribit_options.csv', parse_dates=['date']) 
    for index,row in df_deribit_list.iterrows():
        date=str(row['date'])[:10]
        contract=str(row['option'])
        year=date[:4]
        month=date[5:7]
        file_path = 'data/{}/{}/tick-full-{}-{}.gz'.format(year,month,date, contract.replace('/', '-'))
        download_full_ticks(contract, date, file_path)
        unzip_and_read(file_path)
        print("{} {}".format(date,contract))
    print('finish')

df_options=pd.DataFrame(columns=['date','btc','option','option_data','potion_price'])
def main():
    download_deribit_data()
    pass

    # df_options.to_csv('deribit_options.csv')     
    # print('finish')
    # result=_http_get_request('2022-02-02')
    # print(result)
    # try:
    #     os.makedirs('data')
    # except:
    #     pass
    # date = '2019-12-12'
    # contract = 'okex/eos.eth'

    # simple tick
    # get_contracts(date, 'ticks')
    # file_path = 'data/tick-simple-{}-{}.gz'.format(date, contract.replace('/', '-'))
    # download_simple_ticks(contract, date, file_path)
    # unzip_and_read(file_path)
    #
    # full tick
    # file_path = 'data/tick-full-{}-{}.gz'.format(date, contract.replace('/', '-'))
    # download_full_ticks(contract, date, file_path)
    # unzip_and_read(file_path)
    #
    # # trades
    # get_contracts(date, 'trades')
    # file_path = 'data/trades-{}-{}.gz'.format(date, contract.replace('/', '-'))
    # download_zhubis(contract, date, file_path)
    # unzip_and_read(file_path)
    #
    # candle
    # since = date
    # until = '2019-12-13'
    # download_and_print_candles(contract, since, '2020-10-10', '1m')
if __name__ == '__main__':
    ot_key = load_otkey()
    main()
# time.sleep(10)
