import tkinter as tk
from tkinter import ttk, messagebox
import requests
from bs4 import BeautifulSoup
import ssl
import urllib3
import datetime

# 關閉 SSL 驗證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

rate_data = {}
rate_time = ""

def fetch_rates():
    global rate_time, rate_data
    url = "https://rate.bot.com.tw/xrt?Lang=zh-TW"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print("正在抓取匯率資料...")
        response = requests.get(url, verify=False, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 尋找匯率表格 - 嘗試不同的選擇器
        table = soup.select_one("table.table") or soup.select_one("table")
        if not table:
            print("找不到匯率表格")
            # 輸出部分HTML來除錯
            print("HTML前500字符:", response.text[:500])
            return {}
            
        rows = table.select("tbody tr") or table.select("tr")[1:]
        
        new_data = {}
        print(f"找到 {len(rows)} 行資料")
        
        for i, row in enumerate(rows):
            cols = row.find_all('td')
            if len(cols) < 4:
                print(f"第 {i+1} 行欄位不足: {len(cols)}")
                continue
                
            try:
                first_col = cols[0]
                print(f"第 {i+1} 行第一欄內容: '{first_col.get_text()}'")
                
            
                currency_code = ""
                
                
                full_text = first_col.get_text().strip()
                if '(' in full_text and ')' in full_text:
                    start = full_text.find('(')
                    end = full_text.find(')')
                    if start != -1 and end != -1 and end > start:
                        currency_code = full_text[start+1:end].strip()
                
                # 方法2: 如果找不到括號，嘗試空格分割
                if not currency_code:
                    text_parts = full_text.split()
                    for part in text_parts:
                        if len(part) == 3 and part.isalpha() and part.isupper():
                            currency_code = part
                            break
                
                # 方法3: 尋找特定的HTML結構
                if not currency_code:
                    currency_spans = first_col.find_all('span')
                    for span in currency_spans:
                        text = span.get_text().strip()
                        if len(text) == 3 and text.isalpha() and text.isupper():
                            currency_code = text
                            break
                
                print(f"解析出的貨幣代碼: '{currency_code}'")
                
                if not currency_code or len(currency_code) != 3:
                    print(f"無效的貨幣代碼: '{currency_code}'")
                    continue
                if len(cols) >= 4:
                    cash_buy = cols[2].get_text().strip()
                    cash_sell = cols[3].get_text().strip()
                else:
                    print(f"欄位數量不足: {len(cols)}")
                    continue
                
                print(f"處理貨幣: {currency_code}, 現金買入: {cash_buy}, 現金賣出: {cash_sell}")
                
                if cash_buy and cash_buy != "-" and cash_sell and cash_sell != "-":
                    try:
                        buy_rate = float(cash_buy.replace(',', ''))
                        sell_rate = float(cash_sell.replace(',', ''))
                        
                        new_data[currency_code] = {
                            "buy": buy_rate,
                            "sell": sell_rate
                        }
                        print(f"成功加入 {currency_code}: 買入={buy_rate}, 賣出={sell_rate}")
                        
                    except ValueError as ve:
                        print(f"轉換數值錯誤 {currency_code}: 買入='{cash_buy}', 賣出='{cash_sell}', 錯誤={ve}")
                        continue
                else:
                    print(f"跳過 {currency_code}: 匯率為空或為 '-'")
                        
            except Exception as row_error:
                print(f"處理第 {i+1} 行時發生錯誤: {row_error}")
                print(f"該行HTML: {row}")
                continue
        
        new_data["TWD"] = {"buy": 1.0, "sell": 1.0}
        
        rate_time = ""
        
        for text in soup.find_all(string=True):
            if text and "資料時間" in str(text):
                rate_time = str(text).strip()
                break
        if not rate_time:
            time_selectors = [
                'span.time', '.time', '#time',
                'span[class*="time"]', 'div[class*="time"]'
            ]
            for selector in time_selectors:
                time_elem = soup.select_one(selector)
                if time_elem:
                    rate_time = time_elem.get_text().strip()
                    break

        if not rate_time:
            rate_time = f"資料更新於 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        print(f"成功取得 {len(new_data)} 種貨幣的匯率資料")
        print(f"貨幣列表: {sorted(new_data.keys())}")
        
        if len(new_data) <= 1:  
            print("警告: 只取得到TWD，可能網頁結構已改變")
            print("表格HTML:", str(table)[:1000] if table else "無表格")
        
        return new_data
        
    except requests.exceptions.RequestException as e:
        print(f"網路請求錯誤: {e}")
        return {}
    except Exception as e:
        print(f"解析網頁時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return {}

def update_rates():
    global rate_data
    update_time_label.config(text="正在更新匯率資料...")
    result_label.config(text="載入中...")
    root.update()
    
    new_rate_data = fetch_rates()
    
    if not new_rate_data:
        messagebox.showerror("錯誤", "無法取得匯率資料，請檢查網路連線")
        update_time_label.config(text="匯率更新失敗")
    else:
        rate_data = new_rate_data
        update_time_label.config(text=f"匯率更新時間：{rate_time}")
        result_label.config(text="匯率更新完成")
        currency_list = ["TWD"] + sorted([k for k in rate_data.keys() if k != "TWD"])
        from_currency_box["values"] = currency_list
        to_currency_box["values"] = currency_list
        
        if from_currency_var.get() not in currency_list:
            from_currency_var.set("USD" if "USD" in currency_list else currency_list[0])
        if to_currency_var.get() not in currency_list:
            to_currency_var.set("TWD")
            
        print(f"已更新下拉選單，共 {len(currency_list)} 種貨幣")

def calculate_exchange():
    from_currency = from_currency_var.get()
    to_currency = to_currency_var.get()
    
    try:
        amount = float(amount_entry.get())
    except ValueError:
        result_label.config(text="請輸入有效金額")
        return

    if not rate_data:
        result_label.config(text="請先更新匯率資料")
        return

    if from_currency not in rate_data or to_currency not in rate_data:
        result_label.config(text="找不到所選貨幣的匯率資料")
        return

    try:
        if from_currency == "TWD" and to_currency == "TWD":
            exchanged = amount
        elif from_currency == "TWD":
            exchanged = amount / rate_data[to_currency]["sell"]
        elif to_currency == "TWD":
            exchanged = amount * rate_data[from_currency]["buy"]
        else:
            twd_amount = amount * rate_data[from_currency]["buy"]
            exchanged = twd_amount / rate_data[to_currency]["sell"]

        result_label.config(text=f"{amount:,.2f} {from_currency} ≈ {exchanged:,.4f} {to_currency}")
        
    except Exception as e:
        result_label.config(text=f"轉換錯誤：{str(e)}")

# 建立 UI
root = tk.Tk()
root.title("台銀匯率實時換算工具")
root.geometry("400x300")

main_frame = ttk.Frame(root, padding="20")
main_frame.grid(sticky=(tk.W, tk.E, tk.N, tk.S))

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
main_frame.columnconfigure(1, weight=1)

ttk.Label(main_frame, text="原始貨幣:").grid(column=0, row=0, sticky=tk.W, pady=5)
from_currency_var = tk.StringVar()
from_currency_box = ttk.Combobox(main_frame, textvariable=from_currency_var, state="readonly")
from_currency_box.grid(column=1, row=0, sticky=(tk.W, tk.E), pady=5)

ttk.Label(main_frame, text="目標貨幣:").grid(column=0, row=1, sticky=tk.W, pady=5)
to_currency_var = tk.StringVar()
to_currency_box = ttk.Combobox(main_frame, textvariable=to_currency_var, state="readonly")
to_currency_box.grid(column=1, row=1, sticky=(tk.W, tk.E), pady=5)

ttk.Label(main_frame, text="金額:").grid(column=0, row=2, sticky=tk.W, pady=5)
amount_entry = ttk.Entry(main_frame)
amount_entry.grid(column=1, row=2, sticky=(tk.W, tk.E), pady=5)

button_frame = ttk.Frame(main_frame)
button_frame.grid(column=0, row=3, columnspan=2, pady=15)

ttk.Button(button_frame, text="計算匯率", command=calculate_exchange).grid(column=0, row=0, padx=5)
ttk.Button(button_frame, text="更新匯率", command=update_rates).grid(column=1, row=0, padx=5)

result_label = ttk.Label(main_frame, text="", font=('Arial', 10, 'bold'))
result_label.grid(column=0, row=4, columnspan=2, pady=10)

update_time_label = ttk.Label(main_frame, text="匯率更新時間：尚未更新", font=('Arial', 8))
update_time_label.grid(column=0, row=5, columnspan=2, pady=5)

# 初始化匯率資料
print("正在初始化應用程式...")
update_rates()

# 設定預設值
if rate_data:
    currency_list = list(rate_data.keys())
    if "USD" in currency_list and "TWD" in currency_list:
        from_currency_var.set("USD")
        to_currency_var.set("TWD")
    elif len(currency_list) >= 2:
        from_currency_var.set(currency_list[0])
        to_currency_var.set("TWD" if "TWD" in currency_list else currency_list[1])

amount_entry.bind('<Return>', lambda event: calculate_exchange())

root.mainloop()