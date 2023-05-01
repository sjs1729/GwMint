import streamlit as st
import numpy as np
import pandas as pd
import datetime as dt
from scipy import optimize
import math
from dateutil.relativedelta import relativedelta
import time
import plotly.express as px
from urllib.request import urlopen
import json


np.set_printoptions(precision=3)

st.set_page_config(layout="wide")
tday = dt.datetime.today()

col1, col2 = st.sidebar.columns(2)
col1.image('gw_logo.png', width=300)


months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
tday = dt.date(2023,4,21)

curr_mth = tday.month
curr_mth_year = tday.year

curr_month = months[curr_mth - 1]

if curr_mth == 1:
    prev_mth = 12
    prev_mth_year = curr_mth_year - 1
else:
    prev_mth = curr_mth - 1
    prev_mth_year = curr_mth_year

prev_month = months[prev_mth - 1]

@st.cache_data()
def get_mf_perf():
    df = pd.read_csv('All_Navs.csv')
    df['Date'] = df['Date'].apply(lambda x: dt.datetime.strptime(x,'%Y-%m-%d'))

    df.set_index('Date',inplace=True)

    df_perf = pd.read_csv('revised_mf_perf.csv')
    df_perf.set_index('Scheme_Code', inplace=True)

    df_port_dtl = pd.read_csv('mf_port_detail.csv')

    return df, df_perf, df_port_dtl

@st.cache_data()
def get_schm_mapping_data():
    df_schm_map = pd.read_csv('Scheme_Code_Mapping.csv')
    df_schm_map.set_index('Mint_Scheme',inplace=True)
    return df_schm_map

@st.cache_data()
def get_balance_units_value(amfi_code,bal_units):
    try:
        nav= df_schm_map[df_schm_map['Amfi_Code']==amfi_code]['NAV'].iloc[0]
        bal = round(nav * bal_units,2)
    except:
        bal = 10.0 * bal_units

    return bal

@st.cache_data()
def get_last_5_nav(amfi_code,tday):
    try:
        success = 'N'
        url = 'https://api.mfapi.in/mf/{}'.format(amfi_code)
        response = urlopen(url)
        data_json = json.loads(response.read())

        day_0 = float(data_json['data'][0]['nav'])
        day_1 = float(data_json['data'][1]['nav'])
        day_2 = float(data_json['data'][2]['nav'])
        day_3 = float(data_json['data'][3]['nav'])
        day_4 = float(data_json['data'][4]['nav'])
        day_5 = float(data_json['data'][5]['nav'])

        pct_0 = round(100*(day_0 - day_1)/day_1,2)
        pct_1 = round(100*(day_1 - day_2)/day_2,2)
        pct_2 = round(100*(day_2 - day_3)/day_3,2)
        pct_3 = round(100*(day_3 - day_4)/day_4,2)
        pct_4 = round(100*(day_4 - day_5)/day_5,2)

        success = 'Y'
        result='{}:{}:{}:{}:{}:{}:{}:{}'.format(success,tday,day_0,pct_0,pct_1,pct_2,pct_3,pct_4)

    except:
        result='{}-{}-Exception'.format(success,tday)

    return result

@st.cache_data()
def get_transaction_data():

    progress_text = "Initialising Data..."
    my_bar = st.progress(0.0, text=progress_text)

    df = pd.read_csv('MINT_Transactions.csv')


    df = df[['TRANSACTION DATE', 'SCHEME NAME', 'CATEGORY', 'SUB CATEGORY',
       'FOLIO NO', 'APPLICANT', 'IWELL CODE', 'PAN', 'TXN TYPE', 'AMOUNT',
       'UNITS', 'NAV', 'SB CODE', 'ARN NO', 'ORIGINAL TRANSACTION TYPE',
       'EUIN', 'REMARKS', 'TDS', 'SIP Reg Date', 'STT', 'STAMP DUTY',
       'TOTAL AMOUNT']]

    df['FUND_HOUSE']=df['SCHEME NAME'].apply(lambda x: x.split()[0])
    df['TRAN_DATE'] = df['TRANSACTION DATE'].apply(lambda x: dt.datetime.strptime(x,'%d/%m/%Y'))
    df['Mth']  = df['TRAN_DATE'].apply(lambda x: x.month)
    df['Year'] = df['TRAN_DATE'].apply(lambda x: x.year)
    df = df.sort_values(by=['TRAN_DATE'])

    df_nfty = pd.read_csv('nifty.csv')
    df_nfty['Date']=df_nfty['Date'].apply(lambda x: dt.datetime.strptime(x,'%Y-%m-%d'))

    df['Amfi_Code']=0
    df['Nifty']=0.0
    df['Nifty_Units']=0.0

    total_records = len(df)
    records_processed = 0
    for i in df.index:
        schm_name = df.loc[i]['SCHEME NAME']
        amfi_code = df_schm_map.loc[schm_name]['Amfi_Code']
        t_date = df.loc[i]['TRAN_DATE']
        df.at[i,'Amfi_Code'] = amfi_code
        try:
            nfty_nav = df_nfty[df_nfty['Date'] == t_date]['Close'].iloc[0]
        except:
            nfty_nav = df_nfty[df_nfty['Date'] < t_date]['Close'].tail(1).iloc[0]

        nfty_units = round(df.loc[i]['TOTAL AMOUNT']/nfty_nav,4)
        df.at[i,'Nifty'] = nfty_nav
        df.at[i,'Nifty_Units'] = nfty_units

        records_processed = records_processed + 1
        percent_complete = records_processed/total_records

        if records_processed % 500 == 0:
            progress_text = "{} % Processed".format(round(100*percent_complete,2))
            my_bar.progress(percent_complete, text=progress_text)


    my_bar.progress(1.0, text='100% Processed')
    time.sleep(3)
    my_bar.empty()

    return df

option = st.sidebar.selectbox("Which Dashboard?", ( 'GroWealth','Customer View','Fund House View','Scheme View','Fund Details','Reports','Admin'), 0)
st.title(option)

df_schm_map = get_schm_mapping_data()
df = get_transaction_data()

@st.cache_data()
def display_table(df):
    #st.write(df)

    headercolor = '#008E72'
    odd_rowcolor = '#E5ECF6'
    even_rowcolor = '#D5DCE6'

    fig = go.Figure(data=go.Table(
        header=dict(values=[j for j in df.columns],
        fill_color='#ADD8E6 ',
        align=['center','center'],
        font_size=14
        ),
        cells=dict(values=[df[k] for k in df.columns],
        fill_color= [[odd_rowcolor,even_rowcolor,odd_rowcolor,even_rowcolor,odd_rowcolor,even_rowcolor,odd_rowcolor,even_rowcolor]*25],
        align=['center','center'],
        font_size = 12
        )))
    fig.update_layout(margin=dict(l=1,r=1,b=1,t=1))
    fig.update_layout(height=500)
    fig.update_layout(width=900)


    return fig

def xirr(rate,cash_flow,terminal_value=0):

    npv = 0
    for i in cash_flow.index:
        nYears = cash_flow.loc[i,'Num_Days']/365
        pv = cash_flow.loc[i,'Tran_Value']*(pow((1 + rate / 100), nYears))
        npv = npv + pv

    return  npv+terminal_value

@st.cache_data()
def get_top_cust_schemes():

    rec = []
    for i in df['APPLICANT'].unique():
        df_cust = df[df['APPLICANT'] == i]

        for j in df_cust['SCHEME NAME'].unique():
            df_cust_schm = df_cust[df_cust['SCHEME NAME'] == j]
            amfi_code = df_schm_map.loc[j]['Amfi_Code']
            schm_balance_units = 0.0
            for k in df_cust_schm.index:
                units = df_cust_schm.loc[k]['UNITS']
                if units != units:
                    units = 0.0

                t_type = df_cust_schm.loc[k]['TXN TYPE']
                if t_type in  ['SIP','Systematic Transfer In','Purchase','Switch In']:
                    schm_balance_units = schm_balance_units + units
                elif t_type in  ['SWP','Systematic Transfer Out','Sell','Switch Out']:
                    schm_balance_units = schm_balance_units - units

            if schm_balance_units < 0:
                schm_balance_units=0.0

            bal_units_value = get_balance_units_value(amfi_code,schm_balance_units)


            values = i,j,amfi_code,schm_balance_units,bal_units_value
            rec.append(values)

    df_top_values = pd.DataFrame(rec,columns=['APPLICANT','SCHEME','Amfi_Code','BalUnits','MarketValue'])

    return df_top_values

@st.cache_data()
def get_schm_trans_dtls(txn_type,df_x):

    if txn_type == 'All Transactions':
        df_txn = df_x
    else:
        df_txn = df_x[df_x['TXN TYPE'] == txn_type ]



    rec = []
    log_rec = []
    curr_mth_total = 0
    prev_mth_total = 0
    for applcnt in df_txn['APPLICANT'].unique():
        schm_balance_units = 0
        df_applcnt = df_txn[df_txn['APPLICANT'] == applcnt]
        df_applcnt_x = df_x[df_x['APPLICANT'] == applcnt]

        fh = df_applcnt['FUND_HOUSE'].iloc[0]
        sch_cat = df_applcnt['SUB CATEGORY'].iloc[0]
        amfi_code = df_applcnt['Amfi_Code'].iloc[0]

        df_applcnt['Frequency'] = df_applcnt['TRAN_DATE'].diff()
        df_applcnt['Frequency'] = df_applcnt['Frequency'].apply(lambda x: x.days)

        df_applcnt['Mth'] = df_applcnt['TRAN_DATE'].apply(lambda x: x.month)
        df_applcnt['Year'] = df_applcnt['TRAN_DATE'].apply(lambda x: x.year)
        curr_mth_value = df_applcnt[(df_applcnt['Mth'] == curr_mth ) & (df_applcnt['Year'] == curr_mth_year )]['TOTAL AMOUNT'].sum()
        prev_mth_value = df_applcnt[(df_applcnt['Mth'] == prev_mth ) & (df_applcnt['Year'] == prev_mth_year )]['TOTAL AMOUNT'].sum()

        curr_mth_total = curr_mth_total + curr_mth_value
        prev_mth_total = prev_mth_total + prev_mth_value

        for applcnt_txn in df_applcnt_x.index:
            units = df_applcnt_x.loc[applcnt_txn]['UNITS']
            t_type = df_applcnt_x.loc[applcnt_txn]['TXN TYPE']
            if t_type in  ['SIP','Systematic Transfer In','Purchase','Switch In']:
                schm_balance_units = schm_balance_units + units
            elif t_type in  ['SWP','Systematic Transfer Out','Sell','Switch Out']:
                schm_balance_units = schm_balance_units - units

        if schm_balance_units < 0:
            schm_balance_units=0.0
        bal_units_value = get_balance_units_value(amfi_code,schm_balance_units)
        #bal_units_value = 0

        sys_freq = ''
        sys_status = 'Active'
        if txn_type in  ['SIP', 'SWP','Systematic Transfer In','Systematic Transfer Out']:
            avg_days = df_applcnt['Frequency'].tail(10).mean()

            if avg_days > 0 and  avg_days <= 2:
                sys_freq = 'Daily'
            elif avg_days > 2 and avg_days <= 10:
                sys_freq = 'Weekly'
            elif avg_days > 10 and avg_days <= 20:
                sys_freq = 'Fortnightly'
            elif avg_days > 20 :
                sys_freq = 'Monthly'
            else:
                sys_freq = ''

            if curr_mth_value == 0:
                sys_status = 'Stopped'
            elif curr_mth_value < prev_mth_value/2:
                sys_status = 'Alert - Completed'
            else:
                if txn_type == 'SWP':
                    if bal_units_value < (curr_mth_value):
                        sys_status = 'Alert - Insuffcient Fund for next Month'
                    elif bal_units_value < (2 * curr_mth_value):
                        sys_status = 'Alert - Insuffcient Fund for next 2 Months'
                else:
                    sys_status = 'Active'



        #values = schm, fh, sch_cat, txn_type,round(schm_balance_units,4),round(bal_units_value,2),round(prev_mth_value,2),round(curr_mth_value,2),sys_freq
        values = applcnt, fh, sch_cat,round(schm_balance_units,4),round(bal_units_value,2),display_amount(prev_mth_value),display_amount(curr_mth_value),sys_freq, sys_status
        rec.append(values)
    col_1  = '{} - {}'.format(txn_type,prev_month)
    col_2  = '{} - {}'.format(txn_type,curr_month)
    tran_details = pd.DataFrame(rec, columns=['Customer Name','Fund House','Fund Category','Balance Units',
                                              'Market Value',col_1,col_2,'Frequency','Status'
                                                ])
    tran_details=tran_details.sort_values(by=['Market Value'], ascending=False)

    mkt_val_tot = tran_details['Market Value'].sum()

    tran_details['Market Value'] = tran_details['Market Value'].apply(lambda x: display_amount(x))

    tran_details.loc[len(tran_details)] = ['Overall Schemewise Summary','','','',display_amount(mkt_val_tot),display_amount(prev_mth_total),display_amount(curr_mth_total),'','']

    if txn_type not in  ['SIP', 'SWP','Systematic Transfer In','Systematic Transfer Out']:
        tran_details.drop(columns=[ 'Frequency','Status'],inplace=True)

    return tran_details


@st.cache_data()
def get_transaction_details(txn_type,df_x):

    if txn_type == 'All Transactions':
        df_txn = df_x
    else:
        df_txn = df_x[df_x['TXN TYPE'] == txn_type ]


    rec = []
    log_rec = []
    curr_mth_total = 0
    prev_mth_total = 0
    for schm in df_txn['SCHEME NAME'].unique():
        schm_balance_units = 0
        df_schm = df_txn[df_txn['SCHEME NAME'] == schm]
        df_schm_x = df_x[df_x['SCHEME NAME'] == schm]

        fh = df_schm['FUND_HOUSE'].iloc[0]
        sch_cat = df_schm['SUB CATEGORY'].iloc[0]
        amfi_code = df_schm['Amfi_Code'].iloc[0]

        df_schm['Frequency'] = df_schm['TRAN_DATE'].diff()
        df_schm['Frequency'] = df_schm['Frequency'].apply(lambda x: x.days)

        df_schm['Mth'] = df_schm['TRAN_DATE'].apply(lambda x: x.month)
        df_schm['Year'] = df_schm['TRAN_DATE'].apply(lambda x: x.year)
        curr_mth_value = df_schm[(df_schm['Mth'] == curr_mth ) & (df_schm['Year'] == curr_mth_year )]['TOTAL AMOUNT'].sum()
        prev_mth_value = df_schm[(df_schm['Mth'] == prev_mth ) & (df_schm['Year'] == prev_mth_year )]['TOTAL AMOUNT'].sum()

        curr_mth_total = curr_mth_total + curr_mth_value
        prev_mth_total = prev_mth_total + prev_mth_value

        for schm_txn in df_schm_x.index:
            units = df_schm_x.loc[schm_txn]['UNITS']
            t_type = df_schm_x.loc[schm_txn]['TXN TYPE']
            if t_type in  ['SIP','Systematic Transfer In','Purchase','Switch In']:
                schm_balance_units = schm_balance_units + units
            elif t_type in  ['SWP','Systematic Transfer Out','Sell','Switch Out']:
                schm_balance_units = schm_balance_units - units

        if schm_balance_units < 0:
            schm_balance_units=0.0
        bal_units_value = get_balance_units_value(amfi_code,schm_balance_units)
        #bal_units_value = 0


        sys_freq = ''
        sys_status = 'Active'
        if txn_type in  ['SIP', 'SWP','Systematic Transfer In','Systematic Transfer Out']:
            avg_days = df_schm['Frequency'].tail(10).mean()

            if avg_days > 0 and  avg_days <= 2:
                sys_freq = 'Daily'
            elif avg_days > 2 and avg_days <= 10:
                sys_freq = 'Weekly'
            elif avg_days > 10 and avg_days <= 20:
                sys_freq = 'Fortnightly'
            else:
                sys_freq = 'Monthly'

            if curr_mth_value == 0:
                sys_status = 'Stopped'
            elif curr_mth_value < prev_mth_value/2:
                sys_status = 'Alert - Completed'
            else:
                if txn_type == 'SWP':
                    if bal_units_value < (curr_mth_value):
                        sys_status = 'Alert - Insuffcient Fund for next Month'
                    elif bal_units_value < (2 * curr_mth_value):
                        sys_status = 'Alert - Insuffcient Fund for next 2 Months'
                else:
                    sys_status = 'Active'




        #values = schm, fh, sch_cat, txn_type,round(schm_balance_units,4),round(bal_units_value,2),round(prev_mth_value,2),round(curr_mth_value,2),sys_freq
        values = schm, fh, sch_cat, round(schm_balance_units,4),round(bal_units_value,2),display_amount(prev_mth_value),display_amount(curr_mth_value),sys_freq,sys_status
        rec.append(values)
    col_1  = '{} - {}'.format(txn_type,prev_month)
    col_2  = '{} - {}'.format(txn_type,curr_month)
    tran_details = pd.DataFrame(rec, columns=['Fund Name','Fund House','Fund Category','Balance Units',
                                              'Market Value',col_1,col_2,'Frequency','Status'
                                                ])
    tran_details=tran_details.sort_values(by=['Market Value'], ascending=False)

    mkt_val_tot = tran_details['Market Value'].sum()

    tran_details['Market Value'] = tran_details['Market Value'].apply(lambda x: display_amount(x))

    tran_details.loc[len(tran_details)] = ['Overall Fund Summary','','','',display_amount(mkt_val_tot),display_amount(prev_mth_total),display_amount(curr_mth_total),'','']

    if txn_type not in  ['SIP', 'SWP','Systematic Transfer In','Systematic Transfer Out']:
        tran_details.drop(columns=[ 'Frequency','Status'],inplace=True)

    return tran_details


@st.cache_data()
def get_monthly_details(mth, year):

    df_curr_mth = df[(df['Mth'] == mth ) & (df['Year'] == year )]

    #df_txn_group = df_curr_mth.groupby(by=['TXN TYPE']).sum()['TOTAL AMOUNT']

    mth_sip = df_curr_mth[df_curr_mth['TXN TYPE'] == 'SIP']['TOTAL AMOUNT'].sum()
    mth_pur = df_curr_mth[df_curr_mth['TXN TYPE'] == 'Purchase']['TOTAL AMOUNT'].sum()
    mth_stp_in = df_curr_mth[df_curr_mth['TXN TYPE'] == 'Systematic Transfer In']['TOTAL AMOUNT'].sum()
    mth_swch_in = df_curr_mth[df_curr_mth['TXN TYPE'] == 'Switch In']['TOTAL AMOUNT'].sum()
    mth_swp = df_curr_mth[df_curr_mth['TXN TYPE'] == 'SWP']['TOTAL AMOUNT'].sum()
    mth_sell = df_curr_mth[df_curr_mth['TXN TYPE'] == 'Sell']['TOTAL AMOUNT'].sum()
    mth_stp_out = df_curr_mth[df_curr_mth['TXN TYPE'] == 'Systematic Transfer Out']['TOTAL AMOUNT'].sum()
    mth_swch_out = df_curr_mth[df_curr_mth['TXN TYPE'] == 'Switch Out']['TOTAL AMOUNT'].sum()


    return mth_sip, mth_pur, mth_stp_in, mth_swch_in, mth_swp, mth_sell, mth_stp_out, mth_swch_out

def get_markdown_table(data, header='Y', footer='Y'):


    if header == 'Y':

        cols = data.columns
        ncols = len(cols)
        if ncols < 5:
            html_script = "<table><style> table {border-collapse: collapse;width: 100%; border: 1px solid #ddd;}th {background-color: #ffebcc;padding:0px;} td {font-size='5px;text-align:center;padding:0px;'}tr:nth-child(even) {background-color: #f2f2f2;}</style><thead><tr style='width:100%;border:none;font-family:Courier; color:Red; font-size:15px'>"
        elif ncols < 7:
            html_script = "<table><style> table {border-collapse: collapse;width: 100%; border: 1px solid #ddd;}th {background-color: #ffebcc;padding:0px;} td {font-size='5px;text-align:center;padding:0px;'}tr:nth-child(even) {background-color: #f2f2f2;}</style><thead><tr style='width:100%;border:none;font-family:Courier; color:Red; font-size:13px'>"
        else:
            html_script = "<table><style> table {border-collapse: collapse;width: 100%; border: 1px solid #ddd;}th {background-color: #ffebcc;padding:0px;} td {font-size='5px;text-align:center;padding:0px;'}tr:nth-child(even) {background-color: #f2f2f2;}</style><thead><tr style='width:100%;border:none;font-family:Courier; color:Red; font-size:11px'>"


        for i in cols:
            if 'Fund' in i or 'Name' in i:
                html_script = html_script + "<th style='text-align:left'>{}</th>".format(i)
            else:
                html_script = html_script + "<th style='text-align:center''>{}</th>".format(i)

    html_script = html_script + "</tr></thead><tbody>"
    for j in data.index:
        if ncols < 5:
            html_script = html_script + "<tr style='border:none;font-family:Courier; color:Blue; font-size:13px;padding:1px;';>"
        elif ncols < 7:
            html_script = html_script + "<tr style='border:none;font-family:Courier; color:Blue; font-size:12px;padding:1px;';>"
        else:
            html_script = html_script + "<tr style='border:none;font-family:Courier; color:Blue; font-size:10px;padding:1px;';>"

        a = data.loc[j]
        for k in cols:
            if 'Fund' in k or 'Name' in k:
                html_script = html_script + "<td style='padding:2px;text-align:left' rowspan='1'>{}</td>".format(a[k])
            else:
                html_script = html_script + "<td style='padding:2px;text-align:center' rowspan='1'>{}</td>".format(a[k])

    html_script = html_script + '</tbody></table>'

    return html_script

def get_markdown_dict(dict, font_size = 10, format_amt = 'N'):


    html_script = "<table><style> table {border-collapse: collapse;width: 100%; border: 1px solid #ddd;}th {background-color: #ffebcc;padding:0px;} td {font-size='5px;text-align:center;padding:0px;'}tr:nth-child(even) {background-color: #f2f2f2;}</style><thead><tr style='width:100%;border:none;font-family:Courier; color:Red; font-size:15px'>"

    #html_script = html_script +  "<table><style> th {background-color: #ffebcc;padding:0px;} td {font-size='5px;text-align:center;padding:0px;'}tr:nth-child(even) {background-color: #f2f2f2;}</style><thead><tr style='width:100%;border:none;font-family:Courier; color:Red; font-size:15px'>"

    for j in dict.keys():

        if dict[j] == dict[j]:
            html_script = html_script + "<tr style='border:none;font-family:Courier; color:Blue; font-size:{}px;padding:1px;';>".format(font_size)
            html_script = html_script + "<td style='border:none;padding:2px;font-family:Courier; color:Blue; font-size:{}px;text-align:left' rowspan='1'>{}</td>".format(font_size,j)
            if format_amt == 'N':
                html_script = html_script + "<td style='border:none;padding:4px;font-family:Courier; color:Black; font-size:{}px;text-align:left' rowspan='1'>{}</td>".format(font_size -1,dict[j])
            else:
                html_script = html_script + "<td style='border:none;padding:4px;font-family:Courier; color:Black; font-size:{}px;text-align:right' rowspan='1'>{}</td>".format(font_size -1,display_amount(dict[j]))



    html_script = html_script + '</tbody></table>'

    return html_script


def display_amount(amount):

    if amount != amount:
        amount = 0

    if amount < 0:
        amt_str = '₹ -'
        amount = abs(amount)
    else:
        amt_str = '₹ '

    decimal_part_str = str(round(amount,2)).split(".")

    if len(decimal_part_str) > 1:
        decimal_part = decimal_part_str[1][:2]
        if len(decimal_part) == 1:
            decimal_part = decimal_part.ljust(2,'0')
        else:
            decimal_part = decimal_part.rjust(2,'0')
    else:
        decimal_part = '00'


    amount = round(amount,2)
    cr_amt = int(amount/10000000)
    cr_bal = int(amount - cr_amt * 10000000)

    lkh_amt = int (cr_bal/100000)
    lkh_bal = int(cr_bal - lkh_amt * 100000)

    th_amt  = int(lkh_bal/1000)
    th_bal  = int(lkh_bal - th_amt * 1000)


    if cr_amt > 0:
        if cr_bal > 0:
            amt_str = amt_str + str(cr_amt) + "," + str(lkh_amt).rjust(2,'0') + "," + str(th_amt).rjust(2,'0') + "," + str(th_bal).rjust(3,'0') + "." + decimal_part
        else:
            amt_str = amt_str + str(cr_amt) + ",00,000.00"
    elif lkh_amt > 0:
        if lkh_bal > 0:
            amt_str = amt_str + str(lkh_amt) + "," + str(th_amt).rjust(2,'0') + "," + str(th_bal).rjust(3,'0') + "." + decimal_part
        else:
            amt_str = amt_str + str(lkh_amt) + ",000.00"
    elif th_amt > 0:
        amt_str = amt_str + str(th_amt) + "," + str(th_bal).rjust(3,'0') + "." + decimal_part
    else:
        amt_str = amt_str + str(th_bal) + "." + decimal_part


    return amt_str

@st.cache_data()
def get_xirr():

    gw_cash_flow = []
    gw_mkt_value = 0
    gw_inv_amt   = 0
    xirr_rec = []
    for fh in df['FUND_HOUSE'].unique():
    #for fh in ['ICICI', 'Mirae', 'Axis', 'Canara', 'SBI', 'HDFC', 'Nippon', 'Kotak', 'Quant', 'Motilal']:
    #for fh in ['PGIM']:

        fh_market_value = 0
        fh_invested_amount = 0
        cash_flow_fh = []
        df_fh = df[df['FUND_HOUSE'] == fh]

        for schm in df_fh['SCHEME NAME'].unique():
            df_s = df_fh[df_fh['SCHEME NAME'] == schm]
            df_s = df_s.fillna({'UNITS':0,'TOTAL AMOUNTS':0})
            schm_bal_units = 0.0
            amfi_code = df_schm_map.loc[schm]['Amfi_Code']

            for i in df_s.index:
                s_amount = round(df_s.loc[i]['TOTAL AMOUNT'],2)
                if s_amount != s_amount:
                    s_amount = 0.0

                tran_dt  = df_s.loc[i]['TRAN_DATE']
                tran_dt = tran_dt.to_pydatetime().date()

                tran_typ = df_s.loc[i]['TXN TYPE']
                units    = round(df_s.loc[i]['UNITS'],4)

                if units != units:
                    units = 0.0

                if tran_typ in ['Purchase', 'SIP', 'Systematic Transfer In', 'Bonus', 'Switch In']:
                    cash_flow = -1.0 * s_amount
                    schm_bal_units = schm_bal_units + units
                    fh_invested_amount = fh_invested_amount + s_amount
                elif tran_typ in ['Sell','SWP','Systematic Transfer Out', 'Dividend Payout','Switch Out']:
                    cash_flow = s_amount
                    schm_bal_units = schm_bal_units - units
                    fh_invested_amount = fh_invested_amount - s_amount
                nDays = (tday - tran_dt).days

                values = cash_flow, nDays
                cash_flow_fh.append(values)
                gw_cash_flow.append(values)


            mkt_value = get_balance_units_value(amfi_code,schm_bal_units)

            if mkt_value != mkt_value:
                mkt_value = 0.0

            fh_market_value = fh_market_value + mkt_value
            #st.write(amfi_code,schm,schm_bal_units,mkt_value)

        df_fh_cash_flow = pd.DataFrame(cash_flow_fh,columns=['Tran_Value','Num_Days'])

        #df_fh_cash_flow.to_csv('pgim.csv')
        #st.write(fh_market_value)
        fh_xirr = round(optimize.newton(xirr, 3, args=(df_fh_cash_flow,fh_market_value,)),2)

        rec = fh, display_amount(fh_invested_amount), display_amount(fh_market_value),fh_market_value, fh_xirr
        #st.write(rec)
        xirr_rec.append(rec)

        gw_mkt_value = gw_mkt_value + fh_market_value
        gw_inv_amt   = gw_inv_amt + fh_invested_amount

    df_cash_flow = pd.DataFrame(gw_cash_flow,columns=['Tran_Value','Num_Days'])
    gw_xirr = round(optimize.newton(xirr, 3, args=(df_cash_flow,gw_mkt_value,)),2)

    rec = 'Total', display_amount(gw_inv_amt),display_amount(gw_mkt_value),gw_mkt_value,gw_xirr
    xirr_rec.append(rec)

    df_xirr = pd.DataFrame(xirr_rec,columns=['Fund House','Amount Invested','Market Value','Mkt Value N','XIRR %'])
    #df_xirr = df_xirr.sort_values(by=['Mkt Value N'],ascending=False)
    return df_xirr

@st.cache_data()
def get_scheme_xirr(df_fh):
    fh_market_value = 0
    fh_invested_amount = 0
    cash_flow_fh = []
    xirr_rec = []

    for schm in df_fh['SCHEME NAME'].unique():
        df_s = df_fh[df_fh['SCHEME NAME'] == schm]
        df_s = df_s.fillna({'UNITS':0,'TOTAL AMOUNTS':0})
        schm_bal_units = 0.0
        amfi_code = df_schm_map.loc[schm]['Amfi_Code']
        cash_flow_schm = []
        market_value_schm = 0
        invested_amount_schm = 0

        for i in df_s.index:
            s_amount = round(df_s.loc[i]['TOTAL AMOUNT'],2)
            if s_amount != s_amount:
                s_amount = 0.0

            tran_dt  = df_s.loc[i]['TRAN_DATE']
            tran_dt = tran_dt.to_pydatetime().date()

            tran_typ = df_s.loc[i]['TXN TYPE']
            units    = round(df_s.loc[i]['UNITS'],4)

            if units != units:
                units = 0.0

            if tran_typ in ['Purchase', 'SIP', 'Systematic Transfer In', 'Bonus', 'Switch In']:
                cash_flow = -1.0 * s_amount
                schm_bal_units = schm_bal_units + units
                invested_amount_schm = invested_amount_schm + s_amount
            elif tran_typ in ['Sell','SWP','Systematic Transfer Out', 'Dividend Payout','Switch Out']:
                cash_flow = s_amount
                schm_bal_units = schm_bal_units - units
                invested_amount_schm = invested_amount_schm - s_amount
            nDays = (tday - tran_dt).days

            if nDays == 0:
                nDays = 1

            values = cash_flow, nDays
            cash_flow_schm.append(values)
            cash_flow_fh.append(values)

        mkt_value_schm = get_balance_units_value(amfi_code,schm_bal_units)
        df_cash_flow_schm = pd.DataFrame(cash_flow_schm,columns=['Tran_Value','Num_Days'])
        #if schm == 'HDFC Floating Rate Debt Fund Reg (G)':

        if mkt_value_schm != mkt_value_schm:
            mkt_value_schm = 0.0

        try:
            #st.write(schm,amfi_code,schm_bal_units,invested_amount_schm,mkt_value_schm)
            schm_xirr = round(optimize.newton(xirr, 3, args=(df_cash_flow_schm,mkt_value_schm,)),2)
            #st.write(schm,schm_xirr)
        except:
            st.write(schm,amfi_code,schm_bal_units,invested_amount_schm,mkt_value_schm)
            schm_xirr = 0.0
            df_cash_flow_schm.to_csv("{}.csv".format(schm))

        rec = schm, display_amount(invested_amount_schm), display_amount(mkt_value_schm),mkt_value_schm, schm_xirr
        xirr_rec.append(rec)


        fh_market_value = fh_market_value + mkt_value_schm
        fh_invested_amount = fh_invested_amount + invested_amount_schm


    df_cash_flow_fh = pd.DataFrame(cash_flow_fh,columns=['Tran_Value','Num_Days'])
    fh_xirr = round(optimize.newton(xirr, 3, args=(df_cash_flow_fh,fh_market_value,)),2)
    rec = 'Total', display_amount(fh_invested_amount), display_amount(fh_market_value),fh_market_value, fh_xirr
    xirr_rec.append(rec)

    df_xirr = pd.DataFrame(xirr_rec,columns=['Scheme Name','Invested Amount','Market Value','Market Value N','XIRR %'])

    return df_xirr

@st.cache_data()
def get_rpt_df():
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    df_rpt = df[(df['TXN TYPE'] == 'SWP') | (df['TXN TYPE'] == 'SIP') |(df['TXN TYPE'] == 'Systematic Transfer Out') | (df['TXN TYPE'] == 'Systematic Transfer In') ]

    df_rpt_swp = df_rpt[(df_rpt['TXN TYPE'] == 'SWP')]
    df_rpt_sip = df_rpt[(df_rpt['TXN TYPE'] == 'SIP')]
    df_rpt_sys_in = df_rpt[(df_rpt['TXN TYPE'] == 'SIP') | (df_rpt['TXN TYPE'] == 'Systematic Transfer In') ]
    df_rpt_sys_out = df_rpt[(df_rpt['TXN TYPE'] == 'SWP') | (df_rpt['TXN TYPE'] == 'Systematic Transfer Out') ]

    df_rpt_stp_out = df_rpt[(df_rpt['TXN TYPE'] == 'Systematic Transfer Out')]

    return df_rpt_swp, df_rpt_sip, df_rpt_sys_in, df_rpt_stp_out, df_rpt_sys_out

@st.cache_data()
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')



@st.cache_data()
def get_sys_exhaust(df_rpt_sys,sys_type):

    if sys_type == 'STP':
        sys_type = 'Systematic Transfer Out'

    df_rpt_sys_type = df_rpt_sys[df_rpt_sys['TXN TYPE'] == sys_type]

    rec = []
    for cust in df_rpt_sys_type['APPLICANT'].unique():
        df_cust_sys = df_rpt_sys_type[(df_rpt_sys_type['APPLICANT'] == cust)]

        for schm_nm in df_cust_sys['SCHEME NAME'].unique():

            if sys_type == 'SIP':
                df_cust_sys_schm = df_cust_sys[df_cust_sys['SCHEME NAME'] == schm_nm]
            else:
                df_cust_sys_schm = df_rpt_sys[(df_rpt_sys['SCHEME NAME'] == schm_nm) & (df_rpt_sys['APPLICANT'] == cust) ]

            df_cust_schm = df[(df['SCHEME NAME'] == schm_nm) & (df['APPLICANT'] == cust)]
            amfi_code = df_schm_map.loc[schm_nm]['Amfi_Code']


            curr_mth_value = df_cust_sys_schm[(df_cust_sys_schm['Mth'] == curr_mth ) & (df_cust_sys_schm['Year'] == curr_mth_year )]['TOTAL AMOUNT'].sum()
            prev_mth_value = df_cust_sys_schm[(df_cust_sys_schm['Mth'] == prev_mth ) & (df_cust_sys_schm['Year'] == prev_mth_year )]['TOTAL AMOUNT'].sum()


            #curr_mth_value = df_cust_swp_schm[(df_cust_swp_schm['Mth'] == curr_mth ) & (df_cust_swp_schm['Year'] == curr_mth_year )]['TOTAL AMOUNT'].sum()
            #prev_mth_value = df_cust_swp_schm[(df_cust_swp_schm['Mth'] == prev_mth ) & (df_cust_swp_schm['Year'] == prev_mth_year )]['TOTAL AMOUNT'].sum()

            schm_bal_units = 0.0
            for i in df_cust_schm.index:
                tran_typ = df_cust_schm.loc[i]['TXN TYPE']
                units = df_cust_schm.loc[i]['UNITS']
                if units != units:
                    units = 0.0

                if tran_typ in ['Purchase', 'SIP', 'Systematic Transfer In', 'Bonus', 'Switch In']:
                    schm_bal_units = schm_bal_units + units
                elif tran_typ in ['Sell','SWP','Systematic Transfer Out', 'Dividend Payout','Switch Out']:
                    schm_bal_units = schm_bal_units - units



            mkt_value = get_balance_units_value(amfi_code,round(schm_bal_units,4))
            schm_bal_units = round(schm_bal_units,4)
            if mkt_value <= 0 :
                values = cust, schm_nm, schm_bal_units, display_amount(mkt_value),display_amount(prev_mth_value), display_amount(curr_mth_value), 'Alert:{} Stopped'.format(sys_type)
                rec.append(values)
            elif mkt_value < curr_mth_value and sys_type != 'SIP':
                values = cust, schm_nm, schm_bal_units, display_amount(mkt_value),display_amount(prev_mth_value), display_amount(curr_mth_value), 'Alert:Exhaust in 1 Month'
                rec.append(values)
            elif mkt_value < 2 * curr_mth_value and sys_type != 'SIP':
                values = cust, schm_nm, schm_bal_units, display_amount(mkt_value),display_amount(prev_mth_value), display_amount(curr_mth_value), 'Alert:Exhaust in 2 Months'
                rec.append(values)
            elif curr_mth_value == 0:
                values = cust, schm_nm, schm_bal_units, display_amount(mkt_value),display_amount(prev_mth_value), display_amount(curr_mth_value), 'Alert:{} Stopped'.format(sys_type)
                rec.append(values)
            elif curr_mth_value < 0.75 * prev_mth_value:
                values = cust, schm_nm, schm_bal_units, display_amount(mkt_value),display_amount(prev_mth_value), display_amount(curr_mth_value), 'Alert:{} Likely Stopped or Reduced'.format(sys_type)
                rec.append(values)

            else:
                values = cust, schm_nm, schm_bal_units, display_amount(mkt_value),display_amount(prev_mth_value), display_amount(curr_mth_value), ''
                rec.append(values)


    df_swp_exhaust = pd.DataFrame(rec,columns=['Customer Name','Fund Name','Balance Units',
                                    'Market Value','{} - {}'.format(prev_month,sys_type),'{} - {}'.format(curr_month,sys_type),'STATUS'])
    return df_swp_exhaust

@st.cache_data()
def get_debt_taxation(df_rpt_sys):

    rec = []

    df_rpt_sys = df_rpt_sys[(df_rpt_sys['Mth'] == curr_mth) & (df_rpt_sys['Year'] == curr_mth_year) ]
    debt_tax_schms = [ j for j in
                        df[(df['CATEGORY']=='Other') | (df['CATEGORY']=='Debt') |(df['CATEGORY']=='Gold')
                         | (df['SUB CATEGORY']=='Hybrid: Conservative') ]['SCHEME NAME'].unique()
                     ]
    debt_tax_schms.insert(0,'ICICI Pru Global Advantage Fund (G)')

    for cust in df_rpt_sys['APPLICANT'].unique():
        df_rpt_sys_cust = df_rpt_sys[df_rpt_sys['APPLICANT'] == cust]

        for schm in df_rpt_sys_cust['SCHEME NAME'].unique():

            df_rpt_sys_cust_schm = df_rpt_sys_cust[df_rpt_sys_cust['SCHEME NAME'] == schm]


            for txn_type in df_rpt_sys_cust_schm['TXN TYPE'].unique():

                curr_mth_value = df_rpt_sys_cust_schm[df_rpt_sys_cust_schm['TXN TYPE']==txn_type]['TOTAL AMOUNT'].sum()
                category = df_rpt_sys_cust_schm[df_rpt_sys_cust_schm['TXN TYPE']==txn_type]['CATEGORY'].iloc[0]
                sub_category = df_rpt_sys_cust_schm[df_rpt_sys_cust_schm['TXN TYPE']==txn_type]['SUB CATEGORY'].iloc[0]

                if schm in debt_tax_schms:
                    values = cust, schm, category, sub_category, txn_type, display_amount(curr_mth_value),'Alert:Potential Debt Taxation'
                    rec.append(values)

    df_debt_taxation = pd.DataFrame(rec,columns = ['Customer Name','Scheme Name','Category','Sub Category',
                                                   'Transaction Type','{} Total'.format(curr_month),'Status'
                                                   ])

    return df_debt_taxation

df_mf_data, df_mf_perf, df_port_dtl = get_mf_perf()

if option == 'Customer View':

    s_layout = st.columns((8,2,7))



    cust_list = df['APPLICANT'].unique()

    cust_select = s_layout[0].selectbox("Select Customer",cust_list,0)

    df_cust = df[df['APPLICANT'] == cust_select ]

    txn_list = df_cust['TXN TYPE'].unique()
    txn_list = np.insert(txn_list,0,'All Transactions')

    txn_select = s_layout[2].selectbox("Select Transaction Type",txn_list,0)

    df_cust['TRANSACTION AMOUNT'] = df_cust['TOTAL AMOUNT'].apply(lambda x: display_amount(x))

    rpt_view = ['TRANSACTION DATE', 'SCHEME NAME', 'FUND_HOUSE','SUB CATEGORY', 'TXN TYPE', 'FOLIO NO','UNITS', 'NAV', 'TRANSACTION AMOUNT']


    #df_txntype = df_cust[df_cust['TXN TYPE'] == txn_select ]

    if txn_select == 'All Transactions':
        df_tran_dtl = get_scheme_xirr(df_cust)
        overall_xirr = df_tran_dtl.loc[len(df_tran_dtl)-1]['XIRR %']
        df_tran_dtl.at[len(df_tran_dtl)-1,'XIRR %'] = -100000.00
        df_tran_dtl=df_tran_dtl.sort_values(by=['XIRR %'],ascending=False)
        df_tran_dtl.at[len(df_tran_dtl)-1,'XIRR %'] = overall_xirr
        df_tran_dtl.drop(columns=[ 'Market Value N'],inplace=True)

    else:
        df_tran_dtl = get_transaction_details(txn_select,df_cust )
        df_tran_dtl.at[len(df_tran_dtl)-1,'Fund Name'] = 'Customer Fund Summary'
        df_tran_dtl.at[len(df_tran_dtl)-1,'Status'] = 'XXX'
        df_tran_dtl = df_tran_dtl.sort_values(by=['Status'])
        df_tran_dtl.at[len(df_tran_dtl)-1,'Status'] = ''


    #st.plotly_chart(display_table(df_tran_dtl), use_container_width=True)

    #st.plotly_chart(display_table(df_cust[rpt_view]), use_container_width=True)
    html_script = get_markdown_table(df_tran_dtl)
    st.markdown(html_script,unsafe_allow_html=True)

    csvfile = convert_df(df_tran_dtl)

    st.markdown('<BR>',unsafe_allow_html=True)
    st.download_button(
        label="Download Data as CSV",
        data=csvfile,
        file_name='{}_{}.csv'.format(cust_select,txn_select),
        mime='text/csv',
    )

if option == 'Fund House View':

    s_layout = st.columns((8,2,7))



    fh_list = df['FUND_HOUSE'].unique()

    fh_select = s_layout[0].selectbox("Select Fund House",fh_list,0)

    df_fh = df[df['FUND_HOUSE'] == fh_select ]

    txn_list = df_fh['TXN TYPE'].unique()
    txn_list = np.insert(txn_list,0,'All Transactions')

    txn_select = s_layout[2].selectbox("Select Transaction Type",txn_list,0)

    df_fh['TRANSACTION AMOUNT'] = df_fh['TOTAL AMOUNT'].apply(lambda x: display_amount(x))



    #df_txntype = df_cust[df_cust['TXN TYPE'] == txn_select ]

    df_xirr = get_scheme_xirr(df_fh)

    df_tran_dtl = get_transaction_details(txn_select,df_fh )
    df_tran_dtl.at[len(df_tran_dtl)-1,'Fund Name'] = 'Total'

    df_tran_dtl.drop(columns=[ 'Fund House'],inplace=True)

    df_tran_dtl['Invested Amount'] = ''
    df_tran_dtl['XIRR %'] = 0.0
    for i in df_tran_dtl.index:
        sch_name  = df_tran_dtl.loc[i]['Fund Name']
        inv_amt   = df_xirr[df_xirr['Scheme Name']== sch_name ]['Invested Amount'].iloc[0]
        schm_xirr = df_xirr[df_xirr['Scheme Name']== sch_name ]['XIRR %'].iloc[0]

        df_tran_dtl.at[i,'Invested Amount'] = inv_amt
        df_tran_dtl.at[i,'XIRR %'] = schm_xirr



    cols = [j for j in df_tran_dtl.columns]

    col_xirr = cols.pop()
    col_inv_amt = cols.pop()

    cols.insert(3,col_inv_amt)
    cols.insert(5,col_xirr)

    #st.plotly_chart(display_table(df_tran_dtl), use_container_width=True)

    html_script = get_markdown_table(df_tran_dtl[cols])
    st.markdown(html_script,unsafe_allow_html=True)

    csvfile = convert_df(df_tran_dtl[cols])

    st.markdown('<BR>',unsafe_allow_html=True)
    st.download_button(
        label="Download Data as CSV",
        data=csvfile,
        file_name='{}.csv'.format(fh_select),
        mime='text/csv',
    )

if option == 'Scheme View':

    s_layout = st.columns((8,2,7))



    schm_list = df['SCHEME NAME'].unique()

    schm_select = s_layout[0].selectbox("Select Scheme",schm_list,0)

    df_schm = df[df['SCHEME NAME'] == schm_select ]

    txn_list = df_schm['TXN TYPE'].unique()
    txn_list = np.insert(txn_list,0,'All Transactions')

    txn_select = s_layout[2].selectbox("Select Transaction Type",txn_list,0)

    df_schm['TRANSACTION AMOUNT'] = df_schm['TOTAL AMOUNT'].apply(lambda x: display_amount(x))



    #df_txntype = df_cust[df_cust['TXN TYPE'] == txn_select ]

    df_tran_dtl = get_schm_trans_dtls(txn_select,df_schm)


    #st.plotly_chart(display_table(df_tran_dtl), use_container_width=True)
    html_script = get_markdown_table(df_tran_dtl)
    st.markdown(html_script,unsafe_allow_html=True)

    csvfile = convert_df(df_tran_dtl)

    st.markdown('<BR>',unsafe_allow_html=True)
    st.download_button(
        label="Download Data as CSV",
        data=csvfile,
        file_name='{}_{}.csv'.format(schm_select,txn_select),
        mime='text/csv',
    )


if option == 'GroWealth':

    markdown_text = "<BR><span style='font-family:Courier; font-size: 18px;'><b> Transaction Summary for:</b></span><span style='font-family:Courier; color:Blue; font-size: 16px;'> " + curr_month +"-" + str(curr_mth_year) + "</span>"
    st.markdown(markdown_text,unsafe_allow_html=True)

    sip, pur, stp_in, swch_in, swp, sell, stp_out, swch_out = get_monthly_details(curr_mth, curr_mth_year)

    html_table_1 = "<table style='padding:0px;width=100%;border:none'><tbody style='border:none,padding:0px'>"

    html_table_1 = html_table_1 + "<tr style='padding:1px;border:none;background-color: #ffffff;'><td style='font-family:Courier;font-size:14px;border:none;margin-right:none;'><b>SIP:</b></td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>{}</td>".format(display_amount(sip))
    html_table_1 = html_table_1 + "<td style='padding:20px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>     </td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;border:none'><td style='font-family:Courier;font-size:14px;border:none;margin-right:none;'><b>Purchase:</b></td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>{}</td>".format(display_amount(pur))


    html_table_1 = html_table_1 + "<td style='padding:1px;border:none;background-color: #ffffff;'><td style='font-family:Courier;font-size:14px;border:none;margin-right:none;'><b>STP IN</b></td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>{}</td>".format(display_amount(stp_in))
    html_table_1 = html_table_1 + "<td style='padding:20px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>     </td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;border:none'><td style='font-family:Courier;font-size:14px;border:none;margin-right:none;'><b>Switch IN:</b></td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>{}</td></tr>".format(display_amount(swch_in))

    html_table_1 = html_table_1 + "<tr style='padding:1px;border:none;background-color: #ffffff;'><td style='font-family:Courier;font-size:14px;border:none;margin-right:none;'><b>SWP:</b></td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>{}</td>".format(display_amount(swp))
    html_table_1 = html_table_1 + "<td style='padding:20px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>     </td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;border:none'><td style='font-family:Courier;font-size:14px;border:none;margin-right:none;'><b>Sell:</b></td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>{}</td>".format(display_amount(sell))


    html_table_1 = html_table_1 + "<td style='padding:1px;border:none;background-color: #ffffff;'><td style='font-family:Courier;font-size:14px;border:none;margin-right:none;'><b>STP Out</b></td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>{}</td>".format(display_amount(stp_out))
    html_table_1 = html_table_1 + "<td style='padding:20px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>     </td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;border:none'><td style='font-family:Courier;font-size:14px;border:none;margin-right:none;'><b>Switch Out:</b></td>"
    html_table_1 = html_table_1 + "<td style='padding:1px;font-family:Courier; color:Blue; font-size: 13px;border:none;text-align:left'>{}</td></tr>".format(display_amount(swch_out))

    html_table_1 = html_table_1 + "</tbody></table><BR>"
    st.markdown(html_table_1,unsafe_allow_html=True)

    df_xirr = get_xirr()

    #st.plotly_chart(display_table(df_xirr[['Fund House','Amount Invested','Market Value','XIRR']]), use_container_width=True)

    html_script = get_markdown_table(df_xirr[['Fund House','Amount Invested','Market Value','XIRR %']])
    st.markdown(html_script,unsafe_allow_html=True)

    csvfile = convert_df(df_xirr[['Fund House','Amount Invested','Market Value','XIRR %']])

    st.markdown('<BR>',unsafe_allow_html=True)
    st.download_button(
        label="Download Data as CSV",
        data=csvfile,
        file_name='GroWealth_Perf.csv',
        mime='text/csv',
    )

if option == 'Reports':

    rpt_option = st.selectbox("Reports", ( 'Top25 Schemes','Top25 Customers','SWP Exhaustion Alert','Debt Taxation Report','STP Exhaustion Report','SIP Termination Report','Sourav Das'), 0)

    df_rpt_swp, df_rpt_sip, df_rpt_sys_in, df_rpt_stp_out, df_rpt_sys_out = get_rpt_df()


    if rpt_option == 'Top25 Schemes':

        tday = dt.date.today()
        tday = "{}{}{}".format(tday.year,tday.month,tday.day)
        df_top = get_top_cust_schemes()
        df_top25_schemes = df_top.groupby(by=['SCHEME'])['MarketValue'].sum().sort_values(ascending=False).head(25)
        df_top25_schemes.loc['TOTAL']= df_top25_schemes.sum()
        dict_top25_schemes = df_top25_schemes.round(2).to_dict()

        rec = []

        for i in dict_top25_schemes.keys():
            if i != 'TOTAL':
                amfi_code = df_schm_map.loc[i]['Amfi_Code']
                result = get_last_5_nav(amfi_code,tday)
            else:
                result = 'N'

            res_split = result.split(":")
            if len(res_split) == 8:
                values = i, display_amount(dict_top25_schemes[i]),res_split[2],res_split[3],res_split[4],res_split[5],res_split[6],res_split[7]
            else:
                values = i, display_amount(dict_top25_schemes[i]),'','','','','',''

            rec.append(values)

        df_top25_schm = pd.DataFrame(rec,columns=['Scheme','MarketValue','NAV','Day1_Pct','Day2_Pct','Day3_Pct','Day4_Pct','Day5_Pct'])


        html_text = get_markdown_table(df_top25_schm)
        st.markdown(html_text,unsafe_allow_html=True)





        csvfile = convert_df(df_top25_schm)

        st.markdown('<BR>',unsafe_allow_html=True)
        st.download_button(
            label="Download Data as CSV",
            data=csvfile,
            file_name='Top 25 Schemes.csv',
            mime='text/csv',
        )

    if rpt_option == 'Top25 Customers':

        df_top = get_top_cust_schemes()

        df_top25_cust = df_top.groupby(by=['APPLICANT'])['MarketValue'].sum().sort_values(ascending=False).head(25)
        df_top25_cust.loc['TOTAL']= df_top25_cust.sum()
        dict_top25_cust = df_top25_cust.round(2).to_dict()
        html_text = get_markdown_dict(dict_top25_cust,15,'Y')
        st.markdown(html_text,unsafe_allow_html=True)

        a = [j for j in dict_top25_cust.keys()]
        b = [j for j in dict_top25_cust.values()]

        frame = { 'Top Customers': a, 'Market Value':b}
        result = pd.DataFrame(frame)
        result.set_index('Top Customers', inplace=True)



        csvfile = convert_df(result)

        st.markdown('<BR>',unsafe_allow_html=True)
        st.download_button(
            label="Download Data as CSV",
            data=csvfile,
            file_name='Top 25 Customers.csv',
            mime='text/csv',
        )

    if rpt_option == 'SWP Exhaustion Alert' :
        df_swp_exhaust = get_sys_exhaust(df_rpt_sys_out,'SWP')

        html_script = get_markdown_table(df_swp_exhaust)

        st.markdown(html_script,unsafe_allow_html=True)

        csvfile = convert_df(df_swp_exhaust)

        st.markdown('<BR>',unsafe_allow_html=True)
        st.download_button(
            label="Download Data as CSV",
            data=csvfile,
            file_name='SWP Exhaustion Alert.csv',
            mime='text/csv',
        )

    if rpt_option == 'Debt Taxation Report':
        df_debt_taxation = get_debt_taxation(df_rpt_sys_in)
        html_script = get_markdown_table(df_debt_taxation)

        st.markdown(html_script,unsafe_allow_html=True)

        csvfile = convert_df(df_debt_taxation)

        st.markdown('<BR>',unsafe_allow_html=True)
        st.download_button(
            label="Download Data as CSV",
            data=csvfile,
            file_name='Debt Taxation Report.csv',
            mime='text/csv',
        )

    if rpt_option == 'STP Exhaustion Report':


        df_stp_exhaust = get_sys_exhaust(df_rpt_sys_out,'STP')
        df_stp_exhaust = df_stp_exhaust[df_stp_exhaust['STATUS'] != ''].sort_values(by=['STATUS'])
        html_script = get_markdown_table(df_stp_exhaust)

        st.markdown(html_script,unsafe_allow_html=True)

        csvfile = convert_df(df_stp_exhaust)

        st.markdown('<BR>',unsafe_allow_html=True)
        st.download_button(
            label="Download Data as CSV",
            data=csvfile,
            file_name='Debt Taxation Report.csv',
            mime='text/csv',
        )

    if rpt_option == 'SIP Termination Report':
        df_sip_termination = get_sys_exhaust(df_rpt_sip,'SIP')
        df_sip_termination = df_sip_termination[df_sip_termination['STATUS'] != ''].sort_values(by=['STATUS'])

        html_script = get_markdown_table(df_sip_termination)

        st.markdown(html_script,unsafe_allow_html=True)

        csvfile = convert_df(df_sip_termination)

        st.markdown('<BR>',unsafe_allow_html=True)
        st.download_button(
            label="Download Data as CSV",
            data=csvfile,
            file_name='Debt Taxation Report.csv',
            mime='text/csv',
        )

    if rpt_option == 'Sourav Das':

        df_sd = df[df['APPLICANT'] == 'SOURAV DAS']
        tranch_2_schemes = ['Quant Liquid Fund (G)', 'Axis Bluechip Fund (G)',
                            'ICICI Pru Floating Interest Fund (G)',
                            'Axis Floater Fund Reg (G)', 'SBI Large & Midcap Fund Reg (G)',
                            'ICICI Pru Equity & Debt Fund (G)', 'Quant Absolute Fund (G)',
                            'Quant Active Fund (G)', 'Axis Small Cap Fund Reg (G)',
                            'Axis Growth Opportunities Fund Reg (G)',
                            'ICICI Pru India Opportunities Fund (G)']

        df_sd_tr_1 = df_sd[~df_sd['SCHEME NAME'].isin(tranch_2_schemes)]
        df_sd_tr_2 = df_sd[df_sd['SCHEME NAME'].isin(tranch_2_schemes)]

        df_xirr_tr_1 = get_scheme_xirr(df_sd_tr_1)

        df_xirr_tr_1 = df_xirr_tr_1.drop(columns=['Market Value N'])
        html_script = get_markdown_table(df_xirr_tr_1)

        st.markdown(html_script,unsafe_allow_html=True)

        csvfile = convert_df(df_xirr_tr_1)

        st.markdown('<BR>',unsafe_allow_html=True)
        st.download_button(
            label="Download Tranch 1",
            data=csvfile,
            file_name='Sourav Das Tranch 1',
            mime='text/csv',
        )

        df_xirr_tr_2 = get_scheme_xirr(df_sd_tr_2)
        df_xirr_tr_2 = df_xirr_tr_2.drop(columns=['Market Value N'])

        html_script = get_markdown_table(df_xirr_tr_2)

        st.markdown(html_script,unsafe_allow_html=True)

        csvfile = convert_df(df_sd_tr_2)

        st.markdown('<BR>',unsafe_allow_html=True)
        st.download_button(
            label="Download Tranch 2",
            data=csvfile,
            file_name='Sourav Das Tranch 2',
            mime='text/csv',
        )

if option == 'Fund Details':
    schm_list = df['SCHEME NAME'].unique()

    s_layout = st.columns((13,8))

    schm_select = s_layout[0].selectbox("Select Scheme",schm_list,0)
    comp_date   = s_layout[1].date_input("Select Date", dt.date(2022, 1, 1))
    comp_date = dt.datetime(comp_date.year, comp_date.month, comp_date.day)

    try:

        amfi_code = df_schm_map.loc[schm_select]['Amfi_Code']
        cols = ['Nifty',schm_select]
        df_mf=df_mf_data[df_mf_data.index >= comp_date][cols].dropna()


        df_mf_norm = df_mf * 100 / df_mf.iloc[0]


        fig = px.line(df_mf_norm)


        fig.update_layout(title_text="{} vs Nifty".format(schm_select),
                                  title_x=0.3,
                                  title_font_size=17,
                                  xaxis_title="",
                                  yaxis_title="Value of Rs.100")
        fig.update_layout(showlegend=True)
        fig.update_layout(legend_title='')
        fig.update_layout(legend=dict(
                            x=0.3,
                            y=-0.25,
                            traceorder='normal',
                            font=dict(size=12,)
                         ))

        fig.update_layout(height=500)
        fig.update_layout(width=550)

        s_layout[0].markdown('<BR>',unsafe_allow_html=True)
        s_layout[0].plotly_chart(fig)

        #st.write(df_mf_perf.columns)
        dict_basic_info = {'Fund House': df_mf_perf.loc[amfi_code]['Fund_House'],
                 'Fund Category': df_mf_perf.loc[amfi_code]['Scheme_Category'],
                 'Inception Date': df_mf_perf.loc[amfi_code]['Inception_Date'],
                 'Fund Age': "{} Yrs".format(df_mf_perf.loc[amfi_code]['Age']),
                 'AUM': "{} Cr".format(df_mf_perf.loc[amfi_code]['AUM']),
                 'Expense Ratio': df_mf_perf.loc[amfi_code]['Expense'],
                 'Crisil Rating': df_mf_perf.loc[amfi_code]['CrisilRank'],
                 'Fund Manager': df_mf_perf.loc[amfi_code]['FundManagers']
                }

        html_text = get_markdown_dict(dict_basic_info,12)
        #html_text = '<b>Basic Info</b>' + html_text
        s_layout[1].markdown('<b>Basic Info</b>',unsafe_allow_html=True)

        s_layout[1].markdown(html_text,unsafe_allow_html=True)

        dict_perf_info = {'3M Returns': df_mf_perf.loc[amfi_code]['3M Ret'],
                 '1Y Returns': df_mf_perf.loc[amfi_code]['1Y Ret'],
                 '3Y Returns': df_mf_perf.loc[amfi_code]['3Y Ret'],
                 '5Y Returns': df_mf_perf.loc[amfi_code]['5Y Ret'],
                 '1Y Rolling Returns': df_mf_perf.loc[amfi_code]['Roll_Ret_1Y'],
                 '3Y Rolling Returns': df_mf_perf.loc[amfi_code]['Roll_Ret_3Y'],
                 'Sharpe Ratio': df_mf_perf.loc[amfi_code]['Sharpe Ratio'],
                 'Sortino Ratio': df_mf_perf.loc[amfi_code]['Sortino Ratio'],
                 'Info Ratio': df_mf_perf.loc[amfi_code]['Info Ratio']

                }

        html_text = get_markdown_dict(dict_perf_info,12)

        s_layout[1].markdown('<b>Key Performance</b>',unsafe_allow_html=True)

        s_layout[1].markdown(html_text,unsafe_allow_html=True)

        s_layout = st.columns((4,4,4))

        df_schm_port = df_port_dtl[df_port_dtl['Scheme_Code']==amfi_code]


        dict_port_info_1 = {'No of Stocks': int(df_mf_perf.loc[amfi_code]['NumStocks']),
                     'Equity %': df_mf_perf.loc[amfi_code]['Equity_Holding'],
                     'Large Cap %': round(df_schm_port[df_schm_port['M-Cap']=='Large Cap']['Pct_Holding'].sum(),2),
                     'Mid Cap %': round(df_schm_port[df_schm_port['M-Cap']=='Mid Cap']['Pct_Holding'].sum(),2),
                     'Small Cap %': round(df_schm_port[df_schm_port['M-Cap']=='Small Cap']['Pct_Holding'].sum(),2),
                     'F&O %': df_mf_perf.loc[amfi_code]['F&O_Holding'],
                     'Foreign %': df_mf_perf.loc[amfi_code]['Foreign_Holding'],
                     'Top 5 %': df_mf_perf.loc[amfi_code]['Top5_Pct'],
                     'Debt Modified Duration': df_mf_perf.loc[amfi_code]['Modified_Duration'],
                     'Debt YTM': df_mf_perf.loc[amfi_code]['YTM']
                    }
        html_text = get_markdown_dict(dict_port_info_1,12)

        s_layout[0].markdown('<br>',unsafe_allow_html=True)
        s_layout[0].markdown('<b>Fund Portfolio Summary</b>',unsafe_allow_html=True)
        s_layout[0].markdown(html_text,unsafe_allow_html=True)

        dict_port_info_2 = {'Volatility': round(df_mf_perf.loc[amfi_code]['Volatility'],2),
                     'Beta': df_mf_perf.loc[amfi_code]['Beta'],
                     'Alpha': df_mf_perf.loc[amfi_code]['Alpha'],
                     'R-Squared': df_mf_perf.loc[amfi_code]['R-Squared'],
                     'Pos Year %': df_mf_perf.loc[amfi_code]['Pos_Year%'],
                     'Rel Max Drawdown Nifty':  round(df_mf_perf.loc[amfi_code]['Rel_MaxDD'],2),
                     'Probability >10%': round(df_mf_perf.loc[amfi_code]['Prob_10Pct'],2),
                     'Correl Coeff Nifty': round(df_mf_perf.loc[amfi_code]['NIFTY_CORR'],2),
                     '**** ':'**** ',
                     '****':'****'
                    }
        html_text = get_markdown_dict(dict_port_info_2,12)

        s_layout[1].markdown('<br>',unsafe_allow_html=True)
        s_layout[1].markdown('<b>Fund Volatility Details</b>',unsafe_allow_html=True)
        s_layout[1].markdown(html_text,unsafe_allow_html=True)

        dict_port_info_3 = {'Daily Returns > 1%': round(df_mf_perf.loc[amfi_code]['GT_1PCT'],2),
                     'Daily Returns > 3%': df_mf_perf.loc[amfi_code]['GT_3PCT'],
                     'Daily Returns > 5%': df_mf_perf.loc[amfi_code]['GT_5PCT'],
                     'Daily Returns < -1%': df_mf_perf.loc[amfi_code]['LT_NEG_1PCT'],
                     'Daily Returns < -3%': df_mf_perf.loc[amfi_code]['LT_NEG_3PCT'],
                     'Daily Returns < -5%':  round(df_mf_perf.loc[amfi_code]['LT_NEG_5PCT'],2),
                     'Positive Daily Returns': round(df_mf_perf.loc[amfi_code]['POS_PCT'],2),
                     'Returns > Nifty': round(df_mf_perf.loc[amfi_code]['PCT_GT_NIFTY'],2),
                     'Returns > Nifty+':round(df_mf_perf.loc[amfi_code]['GT_NIFTY_UP'],2),
                     'Returns > Nifty-':round(df_mf_perf.loc[amfi_code]['GT_NIFTY_DOWN'],2)
                    }
        html_text = get_markdown_dict(dict_port_info_3,12)

        s_layout[2].markdown('<br>',unsafe_allow_html=True)
        s_layout[2].markdown('<b>Daily Returns - Statistics</b>',unsafe_allow_html=True)
        s_layout[2].markdown(html_text,unsafe_allow_html=True)


        df_top10_stks = df_schm_port[df_schm_port['Equity_Debt']=='Equity'][['Asset_Name','Pct_Holding']].head(10)
        #df_top10_stks.loc[len(df_top10_stks)]=['Total',df_top10_stks['Pct_Holding'].sum()]

        df_top10_sector = df_schm_port.groupby(by=['Sector']).sum()['Pct_Holding'].sort_values(ascending=False).head(10)
        #df_top10_sector.loc[len(df_top10_sector)] = df_top10_sector.sum()

        df_stk_new_add = df_schm_port[df_schm_port['Status']=='New Addition']['Asset_Name'].head(10)
        df_stk_net_inc = df_schm_port[df_schm_port['Status']=='Increased']['Asset_Name'].head(10)
        df_stk_net_dec = df_schm_port[df_schm_port['Status']=='Decreased']['Asset_Name'].head(10)
        df_stk_removed = df_schm_port[df_schm_port['Status']=='Removed']['Asset_Name'].head(10)



        rec = []
        for i in range(len(df_top10_stks)):
            serial_no = i + 1
            top10_asset = df_top10_stks.iloc[i]['Asset_Name']
            top10_asset_holding = round(df_top10_stks.iloc[i]['Pct_Holding'],2)

            if i < len(df_top10_sector):
                top10_sector = df_top10_sector.index[i]
                top10_sector_holding = round(df_top10_sector.values[i],2)
            else:
                top10_sector = ''
                top10_sector_holding = ''

            if i < len(df_stk_new_add):
                stk_added = df_stk_new_add.values[i]
            else:
                stk_added = ''

            if i < len(df_stk_net_inc):
                stk_increased = df_stk_net_inc.values[i]
            else:
                stk_increased = ''

            if i < len(df_stk_net_dec):
                stk_decreased = df_stk_net_dec.values[i]
            else:
                stk_decreased = ''

            if i < len(df_stk_removed):
                stk_removed = df_stk_removed.values[i]
            else:
                stk_removed = ''



            values = i+1, top10_asset, top10_asset_holding, top10_sector, top10_sector_holding,  \
                          stk_added, stk_increased, stk_decreased, stk_removed
            rec.append(values)

        values = 'Total','',round(df_top10_stks['Pct_Holding'].sum(),2),'',round(df_top10_sector.sum(),2),'','','',''
        rec.append(values)

        df_top10_port = pd.DataFrame(rec,columns=['Serial','Top10 Stocks','Top10 Stock %', 'Top10 Sectors','Top10 Sector %',    \
                                                  'Stocks Added', 'Stocks Increased','Stocks Decreased','Stocks Removed'
                                                 ])
        html_script = get_markdown_table(df_top10_port)

        st.markdown('<BR><BR>Fund Portfolio Details',unsafe_allow_html=True)
        st.markdown(html_script,unsafe_allow_html=True)
        #s_layout[2].write(df_top10_sector.index)
    except:
        st.markdown('<BR><BR>*** Data Not Available for {}'.format(schm_select),unsafe_allow_html=True)

if option == 'Admin':

    tday = dt.date.today()
    tday = "{}{}{}".format(tday.year,tday.month,tday.day)


    if st.button('Latest NAV'):
        total_records = len(df_schm_map)
        progress_text = "Updating NAV"
        my_bar = st.progress(0.0, text=progress_text)
        records_processed = 0
        for i in df_schm_map.index:
            amfi_code = df_schm_map.loc[i]['Amfi_Code']
            result = get_last_5_nav(amfi_code,tday)

            result_str = result.split(":")

            if result_str[0] == 'Y':
                latest_nav = float(result_str[2])
                df_schm_map.at[i,'NAV'] = latest_nav


            records_processed = records_processed + 1
            percent_complete = round(records_processed/total_records,4)

            progress_text = "{} % Processed".format(int(100*percent_complete))
            my_bar.progress(percent_complete, text=progress_text)


        df_schm_map.to_csv('Scheme_Code_Mapping.csv')
        my_bar.progress(1.0, text='100% Processed')
