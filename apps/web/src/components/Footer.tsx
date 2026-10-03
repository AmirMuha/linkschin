import React from 'react'
import Link from 'next/link'

export function Footer() {
  return (
    <footer className="ftr" data-od-id="site-footer">
      <div className="wrap">
        <div className="ftr-grid">
          <div>
            <Link className="brand" href="/" aria-label="لینک‌چین، صفحه اصلی">
              <img
                src="/images/brand/logo-with-text.png"
                alt="لینک‌چین — فیلم، بازی، موسیقی"
                width={180}
                height={180}
                style={{ height: 'auto', maxWidth: '180px' }}
              />
            </Link>
            <p style={{ marginTop: '16px' }}>
              یک گردآورنده لینک مستقیم برای پورتال‌های فیلم، بازی و موسیقی ایرانی.
              این سرور حتی یک بایت از رسانه را ذخیره، میزبانی، پروکسی یا بازارسال نمی‌کند — هر لینک
              مستقیماً از مرورگر شما به CDN مبدأ می‌رسد.
            </p>
          </div>
          <div>
            <h3>کاوش</h3>
            <ul>
              <li>
                <a href="#movies">فیلم و سریال</a>
              </li>
              <li>
                <a href="#games">بازی‌ها</a>
              </li>
              <li>
                <a href="#music">موسیقی</a>
              </li>
              <li>
                <Link href="/favorites">علاقه‌مندی‌ها</Link>
              </li>
              <li>
                <Link href="/youtube-to-mp3">
                  <span dir="ltr">YouTube → MP3</span>
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <h3>قوانین و اطلاعات</h3>
            <ul>
              <li>
                <Link href="/sources">فهرست منابع</Link>
              </li>
              <li>
                <Link href="/sources#suggest">پیشنهاد منبع جدید</Link>
              </li>
              <li>
                <a href="#faq">سوالات متداول</a>
              </li>
              <li>
                <Link href="/sources#legal">سیاست محتوا</Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="ftr-base">
          <span>
            <span dir="ltr">© 2026 Linkschin</span> · گردآورنده لینک مستقیم
          </span>
          <span>
            این سایت هیچ رسانه‌ای ذخیره نمی‌کند. تمامی فراداده‌های فهرست از مبدأ دریافت می‌شود.
          </span>
        </div>
      </div>
    </footer>
  )
}
