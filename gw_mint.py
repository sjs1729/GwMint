import streamlit as st
import numpy as np
import pandas as pd
import datetime as dt
from scipy import optimize
import math
from dateutil.relativedelta import relativedelta
import time


np.set_printoptions(precision=3)

st.set_page_config(layout="wide")
tday = dt.datetime.today()

col1, col2 = st.sidebar.columns(2)
col1.image('gw_logo.png', width=300)


months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
tday = dt.date(2023,3,31)

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
def get_schm_mapping_data():
    df_schm_map = pd.read_csv('Scheme_Code_Mapping.csv')
    df_schm_map.set_index('Mint_Scheme',inplace=True)
    return df_schm_map

@st.cache_data()
def get_balance_units_value(amfi_code,bal_units):
    try:
        nav=df_schm_map[df_schm_map['Amfi_Code']==amfi_code]['NAV'].iloc[0]
        bal = round(nav * bal_units,2)
    except:
        bal = 10.0 * bal_units

    return bal

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

option = st.sidebar.selectbox("Which Dashboard?", ( 'GroWealth','Customer View','Fund House View','Scheme View','Reports'), 0)
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

    df_x = df
    df_x['Mth'] = df_x['TRAN_DATE'].apply(lambda x: x.month)
    df_x['Year'] = df_x['TRAN_DATE'].apply(lambda x: x.year)
    df_curr_mth = df_x[(df_x['Mth'] == mth ) & (df_x['Year'] == year )]
    df_txn_group = df_curr_mth.groupby(by=['TXN TYPE']).sum()['TOTAL AMOUNT']

    mth_sip = df_txn_group['SIP']
    mth_pur = df_txn_group['Purchase']
    mth_stp_in = df_txn_group['Systematic Transfer In']
    mth_swch_in = df_txn_group['Switch In']

    mth_swp = df_txn_group['SWP']
    mth_sell = df_txn_group['Sell']
    mth_stp_out = df_txn_group['Systematic Transfer Out']
    mth_swch_out = df_txn_group['Switch Out']

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


def display_amount(amount):

    if amount != amount:
        amount = 0

    if amount < 0:
        amt_str = '₹ -'
        amount = abs(amount)
    else:
        amt_str = '₹ '

    decimal_part_str = str(amount - int(amount)).split(".")

    if len(decimal_part_str) > 1:
        decimal_part = decimal_part_str[1][:2]
    else:
        decimal_part = decimal_part_str[0][:2]


    amount = round(amount,2)
    cr_amt = int(amount/10000000)
    cr_bal = int(amount - cr_amt * 10000000)

    lkh_amt = int (cr_bal/100000)
    lkh_bal = int(cr_bal - lkh_amt * 100000)

    th_amt  = int(lkh_bal/1000)
    th_bal  = int(lkh_bal - th_amt * 1000)


    print(cr_amt,cr_bal,lkh_amt,lkh_bal,th_amt,th_bal, decimal_part)
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

    df_xirr = pd.DataFrame(xirr_rec,columns=['Fund House','Amount Invested','Market Value','Mkt Value N','XIRR'])
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

    df_xirr = pd.DataFrame(xirr_rec,columns=['Scheme Name','Invested Amount','Market Value','Market Value N','XIRR'])

    return df_xirr

@st.cache_data()
def get_rpt_df():
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    df_rpt = df[(df['TXN TYPE'] == 'SWP') | (df['TXN TYPE'] == 'SIP') |(df['TXN TYPE'] == 'Systematic Transfer Out') | (df['TXN TYPE'] == 'Systematic Transfer In') ]
    df_rpt['Mth']  = df_rpt['TRAN_DATE'].apply(lambda x: x.month)
    df_rpt['Year'] = df_rpt['TRAN_DATE'].apply(lambda x: x.year)

    df_rpt_swp = df_rpt[(df_rpt['TXN TYPE'] == 'SWP')]
    df_rpt_sip = df_rpt[(df_rpt['TXN TYPE'] == 'SIP')]
    df_rpt_sys = df_rpt[(df_rpt['TXN TYPE'] == 'SIP') | (df_rpt['TXN TYPE'] == 'Systematic Transfer In') ]
    df_rpt_stp_out = df_rpt[(df_rpt['TXN TYPE'] == 'Systematic Transfer Out')]

    return df_rpt_swp, df_rpt_sip, df_rpt_sys, df_rpt_stp_out

@st.cache_data()
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')



@st.cache_data()
def get_sys_exhaust(df_rpt_swp,sys_type):

    rec = []
    for cust in df_rpt_swp['APPLICANT'].unique():
        df_cust_swp = df_rpt_swp[df_rpt_swp['APPLICANT'] == cust]

        for schm_nm in df_cust_swp['SCHEME NAME'].unique():
            df_cust_swp_schm = df_cust_swp[df_cust_swp['SCHEME NAME'] == schm_nm]
            df_cust_schm = df[(df['SCHEME NAME'] == schm_nm) & (df['APPLICANT'] == cust)]
            amfi_code = df_schm_map.loc[schm_nm]['Amfi_Code']
            curr_mth_value = df_cust_swp_schm[(df_cust_swp_schm['Mth'] == curr_mth ) & (df_cust_swp_schm['Year'] == curr_mth_year )]['TOTAL AMOUNT'].sum()
            prev_mth_value = df_cust_swp_schm[(df_cust_swp_schm['Mth'] == prev_mth ) & (df_cust_swp_schm['Year'] == prev_mth_year )]['TOTAL AMOUNT'].sum()

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



            mkt_value = get_balance_units_value(amfi_code,schm_bal_units)
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
    df_tran_dtl['XIRR'] = 0.0
    for i in df_tran_dtl.index:
        sch_name  = df_tran_dtl.loc[i]['Fund Name']
        inv_amt   = df_xirr[df_xirr['Scheme Name']== sch_name ]['Invested Amount'].iloc[0]
        schm_xirr = df_xirr[df_xirr['Scheme Name']== sch_name ]['XIRR'].iloc[0]

        df_tran_dtl.at[i,'Invested Amount'] = inv_amt
        df_tran_dtl.at[i,'XIRR'] = schm_xirr



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

    html_script = get_markdown_table(df_xirr[['Fund House','Amount Invested','Market Value','XIRR']])
    st.markdown(html_script,unsafe_allow_html=True)

    csvfile = convert_df(df_xirr[['Fund House','Amount Invested','Market Value','XIRR']])

    st.markdown('<BR>',unsafe_allow_html=True)
    st.download_button(
        label="Download Data as CSV",
        data=csvfile,
        file_name='GroWealth_Perf.csv',
        mime='text/csv',
    )

if option == 'Reports':

    rpt_option = st.selectbox("Reports", ( 'SWP Exhaustion Alert','Debt Taxation Report','STP Exhaustion Report','SIP Termination Report'), 0)

    df_rpt_swp, df_rpt_sip, df_rpt_sys, df_rpt_stp_out = get_rpt_df()


    if rpt_option == 'SWP Exhaustion Alert' :
        df_swp_exhaust = get_sys_exhaust(df_rpt_swp,'SWP')

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
        df_debt_taxation = get_debt_taxation(df_rpt_sys)
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


        df_stp_exhaust = get_sys_exhaust(df_rpt_stp_out,'STP')
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
