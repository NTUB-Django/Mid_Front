# NTUB 課表系統

Django 校園課表與行程管理專案。學生可查課、匯入班級或 Excel 課表、管理好友及群組；學校端可管理班級、開課名額及匯入學生。

## 本機啟動

需要 Python 3.10 以上與網路連線。下載專案後，在專案目錄執行：

```sh
python run.py
```

首次執行會建立虛擬環境、安裝 `requirements.txt`、建立本機 SQLite 資料庫、匯入 `data/ntub/courses_raw.jsonl` 並建立展示帳號。網站位於 `http://127.0.0.1:8000/`；按 Ctrl+C 停止。再次啟動會保留既有資料。

僅完成安裝與初始化：`python run.py setup`。重新安裝套件：`python run.py setup --reinstall`。檢查環境：`python run.py check`。

## 本機展示帳號

| 身分 | 登入識別 | 密碼 | 入口 |
| --- | --- | --- | --- |
| 管理員 | admin | admin1234 | `/admin/` |
| 學校端 | school@example.com | school123 | `/school/` |
| 學生 | student@example.com | student123 | `/accounts/login/` |

展示帳號只供本機使用。除最高管理員 `admin` 外，正式登入一律使用 Email 與密碼；目前不要求 Email 驗證。註冊學生帳號時仍須填學號與 Email，成功後會自動登入。三個入口有獨立的瀏覽器登入狀態。

## 課表與行程

課程查詢可依關鍵字、學制、系所與年級篩選。學生可匯入班級或 Excel 課表，在確認前預覽重複資料與時間衝突，並撤銷匯入或批次刪除匯入課程。固定課表與日期行程分開儲存，日曆提供日、週、月與清單檢視，時間使用 24 小時制。好友、同班同學及群組分享由各項可見設定控制，存取權限在後端驗證。

課程資料位於 `data/ntub/courses_raw.jsonl`。本機資料庫、金鑰與環境檔不納入版本控制。
