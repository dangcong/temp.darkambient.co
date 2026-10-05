# Darkambient Temp Mail Deployment

Runtime này triển khai giao diện tại `https://temp.darkambient.co` và nhận mọi địa chỉ `@temp.darkambient.co` trên VPS `89.117.21.223`. MX của apex `darkambient.co` vẫn thuộc Google Workspace.

## DNS

Tạo các record sau trong Cloudflare:

| Type | Name | Content | Mode |
| --- | --- | --- | --- |
| A | `temp` | `89.117.21.223` | Proxied |
| A | `mx.temp` | `89.117.21.223` | DNS only |
| MX | `temp` | `mx.temp.darkambient.co` priority `10` | DNS only |
| TXT | `temp` | `v=spf1 mx -all` | DNS only |
| TXT | `_dmarc.temp` | `v=DMARC1; p=none; rua=mailto:postmaster@temp.darkambient.co; adkim=s; aspf=s` | DNS only |
| TXT | `mail._domainkey.temp` | Nội dung public record từ DKIM `mail.txt` do DMS tạo | DNS only |

Đổi PTR/rDNS của `89.117.21.223` thành `mx.temp.darkambient.co` trong control panel của nhà cung cấp VPS. Không sửa các MX record của `darkambient.co`.

## Runtime layout

- App source: `/opt/darkambient-temp-mail/app`
- Compose: `/opt/darkambient-temp-mail/app/deploy/darkambient/compose.yaml`
- App secrets: `/opt/darkambient-temp-mail/app/deploy/darkambient/.env`
- Credential handoff: `/opt/darkambient-temp-mail/app/deploy/darkambient/credentials.txt`
- App/SQLite data: `/opt/darkambient-temp-mail/app/deploy/darkambient/data/app`
- Mail data: `/opt/darkambient-temp-mail/app/deploy/darkambient/data/mail-data`
- DMS config, account hashes, DKIM: `/opt/darkambient-temp-mail/app/deploy/darkambient/data/dms-config`
- Pre-deploy backups: `/opt/darkambient-temp-mail/backups`

`.env` và `credentials.txt` phải có mode `600`. Không commit hoặc gửi các file này lên GitHub.

## Git checkout và cập nhật

Repo vận hành chính thức là `https://github.com/dangcong/temp.darkambient.co`. Cả local và VPS đều dùng branch `main` tracking `origin/main`; VPS checkout đặt tại `/opt/darkambient-temp-mail/app`. Runtime `.env`, credentials và `data/` luôn nằm trong các path đã ignore, nên `git pull` không được phép ghi đè chúng.

Sau khi test và push từ local, cập nhật VPS bằng:

```bash
cd /opt/darkambient-temp-mail/app
sudo bash deploy/darkambient/update.sh
```

Script chỉ nhận fast-forward từ `origin/main`, từ chối chạy khi tracked worktree có thay đổi, kiểm tra Compose config, rebuild riêng app, rồi yêu cầu health endpoint public trả về thành công. Mailserver và dữ liệu mail không bị recreate trong update code thông thường.

## Provision DKIM cho Rspamd

Phải chạy helper trong mailserver đang hoạt động để dùng đúng backend Rspamd (`ENABLE_RSPAMD=1`, `ENABLE_OPENDKIM=0`) và reload signer. Chạy image rời không có env này sẽ tạo nhầm key cho OpenDKIM và mail outbound sẽ không được Rspamd ký.

```bash
cd /opt/darkambient-temp-mail/app/deploy/darkambient
docker exec darkambient-mailserver setup config dkim domain temp.darkambient.co
sed -i 's/use_esld = true;/use_esld = false;/' data/dms-config/rspamd/override.d/dkim_signing.conf
docker exec darkambient-mailserver supervisorctl restart rspamd
find data/dms-config/rspamd/dkim -maxdepth 1 -type f -ls
```

`use_esld = false` giữ nguyên sender domain `temp.darkambient.co`; nếu để `true`, Rspamd chuẩn hóa thành apex `darkambient.co` và không tìm thấy key map của subdomain. Sau khi cập nhật TXT `mail._domainkey.temp.darkambient.co` bằng public key mới, restart Rspamd lần nữa để xóa DNS cache rồi xác minh `DKIM check: pass` từ một verifier bên ngoài.

## Start và status

```bash
cd /opt/darkambient-temp-mail/app/deploy/darkambient
docker compose -f compose.yaml config --quiet
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml ps
docker logs --tail 100 darkambient-mailserver
docker logs --tail 100 darkambient-temp-app
```

## DNS verification

```powershell
Resolve-DnsName darkambient.co -Type MX
Resolve-DnsName temp.darkambient.co -Type A
Resolve-DnsName temp.darkambient.co -Type MX
Resolve-DnsName temp.darkambient.co -Type TXT
Resolve-DnsName mail._domainkey.temp.darkambient.co -Type TXT
Resolve-DnsName _dmarc.temp.darkambient.co -Type TXT
Resolve-DnsName 223.21.117.89.in-addr.arpa -Type PTR
```

Kỳ vọng: apex MX vẫn là Google; `temp` MX trỏ `mx.temp.darkambient.co`; SPF, DKIM và DMARC xuất hiện; PTR khớp mail hostname.

## Service verification

```bash
docker exec darkambient-temp-app python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8010/api/health', timeout=10).read().decode())"
curl -fsS https://temp.darkambient.co/api/health
ss -ltnp
```

Từ Internet chỉ được mở `22`, `25`, `80`, `443`. Các cổng `587`, `993`, `8012` phải đóng; app dùng `587/993` qua Docker network nội bộ.

Kiểm thử mail gồm:

1. Gửi một email từ hệ thống bên ngoài tới hai alias chưa tạo trước tại `@temp.darkambient.co`; xác nhận cả hai inbox mở được cùng message với đúng alias đang chọn.
2. Xác nhận subject, body, OTP/link và attachment xuất hiện trong app.
3. Dùng admin UI để send mới, reply và forward bằng alias nguồn; kiểm tra giới hạn 10 tệp và tổng 18 MB.
4. Tạo forwarding rule từ nhiều alias tới nhiều email ngoài domain, gửi thư mới và xác nhận từng target được ghi nhận độc lập. Target thuộc `@temp.darkambient.co` phải bị từ chối.
5. Kiểm tra Authentication-Results của mail nhận: SPF/DKIM/DMARC.
6. Thử relay không xác thực với sender và recipient đều ngoài domain; server phải trả `5xx` và không queue mail.

Forwarding chỉ enqueue cho thư mới sau khi rule được bật. Target lỗi được retry theo backoff từ 30 giây, tối đa 1 giờ; xem trạng thái gần nhất trong admin UI và log app bằng:

```bash
cd /opt/darkambient-temp-mail/app/deploy/darkambient
docker logs --tail 200 darkambient-temp-app
```

## Backup

```bash
cd /opt/darkambient-temp-mail/app/deploy/darkambient
stamp="$(date +%Y%m%d%H%M%S)"
mkdir -p "/opt/darkambient-temp-mail/backups/$stamp"
docker compose -f compose.yaml stop
tar -C data -czf "/opt/darkambient-temp-mail/backups/$stamp/runtime-data.tgz" app mail-data mail-state dms-config
docker compose -f compose.yaml start
sha256sum "/opt/darkambient-temp-mail/backups/$stamp/runtime-data.tgz" > "/opt/darkambient-temp-mail/backups/$stamp/runtime-data.tgz.sha256"
```

Backup khi stack dừng ngắn giúp SQLite và mailbox có snapshot nhất quán.

## Credential rotation

Đổi admin/user bằng API quản trị sau khi login hoặc cập nhật account trong SQLite qua UI quản lý người dùng. Đổi mailbox password bằng DMS CLI, sau đó cập nhật đồng thời `IMAP_PASSWORD` và `SMTP_PASSWORD` trong `.env` rồi recreate app:

```bash
cd /opt/darkambient-temp-mail/app/deploy/darkambient
docker exec -it darkambient-mailserver setup email update contact@temp.darkambient.co
docker compose -f compose.yaml up -d --force-recreate app
```

## Rollback

Rollback không đụng Google Workspace:

```bash
cd /opt/darkambient-temp-mail/app/deploy/darkambient
docker compose -f compose.yaml down
rm -f /etc/nginx/sites-enabled/temp.darkambient.co.conf
nginx -t
systemctl reload nginx
```

Sau đó xóa riêng A/MX/TXT của `temp.darkambient.co` và `mx.temp.darkambient.co` trong Cloudflare. Giữ nguyên thư mục `data/` và backup để có thể phục hồi.
