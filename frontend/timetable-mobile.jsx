import React, { useState } from "react";
import { createRoot } from "react-dom/client";

const root = document.getElementById("mobile-timetable-root");
const dataNode = document.getElementById("mobile-timetable-data");

function EventCard({ event, editable }) {
  const content = (
    <>
      <div className="mobile-agenda-card__time">
        <strong>{event.start}</strong>
        <span>{event.end}</span>
      </div>
      <div className="mobile-agenda-card__body">
        <span className="mobile-agenda-card__code">{event.isCustom ? "個人行程" : event.code}</span>
        <h3>{event.name}</h3>
        {(event.room || event.teacher) && (
          <p>{[event.room, event.teacher].filter(Boolean).join("・")}</p>
        )}
        {event.notes && <p className="mobile-agenda-card__notes">{event.notes}</p>}
      </div>
      <span className="mobile-agenda-card__period">{event.period}</span>
    </>
  );

  if (event.isCustom && editable) {
    return <button type="button" className={`mobile-agenda-card tt-card-${event.color}`} onClick={() => document.dispatchEvent(new CustomEvent('schedule:edit', {detail: {id: event.customId}}))} aria-label={`編輯行程：${event.name}`}>{content}</button>;
  }
  return event.url ? (
    <a className={`mobile-agenda-card tt-card-${event.color}`} href={event.url}>{content}</a>
  ) : (
    <article className={`mobile-agenda-card tt-card-${event.color}`}>{content}</article>
  );
}

function MobileTimetable({ days, editable }) {
  const todayIndex = days.findIndex((day) => day.isToday);
  const firstBusyIndex = days.findIndex((day) => day.events.length > 0);
  const [activeIndex, setActiveIndex] = useState(
    todayIndex >= 0 ? todayIndex : Math.max(firstBusyIndex, 0),
  );
  const activeDay = days[activeIndex];

  return (
    <section className="mobile-agenda" aria-label="手機每日課表">
      <div className="mobile-agenda__heading">
        <div>
          <h2>我的課表</h2>
          <p>選擇日期查看課程與行程</p>
        </div>
        <span>{activeDay.events.length} 項</span>
      </div>
      <div className="mobile-agenda__days" role="tablist" aria-label="選擇星期">
        {days.map((day, index) => (
          <button
            key={day.weekday}
            type="button"
            role="tab"
            aria-selected={index === activeIndex}
            aria-controls="mobile-agenda-events"
            className={`mobile-agenda__day${index === activeIndex ? " is-active" : ""}${day.isToday ? " is-today" : ""}`}
            onClick={() => setActiveIndex(index)}
          >
            <span>{day.label.slice(1)}</span>
            {day.isToday && <small>今天</small>}
          </button>
        ))}
      </div>
      <div id="mobile-agenda-events" className="mobile-agenda__events" role="tabpanel">
        {activeDay.events.length ? (
          activeDay.events.map((event) => <EventCard key={event.id} event={event} editable={editable} />)
        ) : (
          <div className="mobile-agenda__empty">
            <strong>{activeDay.isToday ? "今天沒有排定課程" : `${activeDay.label}沒有排定課程`}</strong>
            <span>選擇其他日期查看一週安排。</span>
          </div>
        )}
      </div>
      {editable && <button type="button" className="mobile-agenda-create" onClick={() => document.dispatchEvent(new CustomEvent('schedule:create', {detail: {weekday: activeDay.weekday}}))}>＋ 在{activeDay.label}新增行程</button>}
    </section>
  );
}

if (root && dataNode) {
  try {
    root.parentElement?.classList.add("mobile-agenda-ready");
    createRoot(root).render(<MobileTimetable days={JSON.parse(dataNode.textContent)} editable={root.dataset.editable === 'true'} />);
  } catch (error) {
    console.error("無法載入手機課表", error);
  }
}
