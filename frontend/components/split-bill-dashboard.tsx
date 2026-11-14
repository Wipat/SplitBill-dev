"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { api, type Balance, type Expense, type Group, type User } from "@/lib/api";
import {
  centsToDecimalString,
  formatCents,
  parseCents,
  parseSignedCents,
  splitEqualCents,
} from "@/lib/money";

const STORAGE_KEY = "splitbill.userId";

function formatApiMoney(value: string): string {
  const cents = parseSignedCents(value);
  return cents === null ? value : formatCents(cents);
}

export default function SplitBillDashboard() {
  const [users, setUsers] = useState<User[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [balances, setBalances] = useState<Balance[]>([]);
  const [description, setDescription] = useState("");
  const [amountInput, setAmountInput] = useState("");
  const [payerId, setPayerId] = useState<number | null>(null);
  const [splitType, setSplitType] = useState<"equal" | "exact">("equal");
  const [participantIds, setParticipantIds] = useState<number[]>([]);
  const [exactInputs, setExactInputs] = useState<Record<number, string>>({});
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingGroup, setLoadingGroup] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deletingExpenseId, setDeletingExpenseId] = useState<number | null>(null);
  const [pageError, setPageError] = useState("");
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState("");

  const selectedGroup = groups.find((group) => group.id === selectedGroupId);
  const groupUsers = selectedGroup?.members ?? [];
  const totalCents = parseCents(amountInput);
  const exactCents = useMemo(() => {
    const entries = participantIds.map((id) => parseCents(exactInputs[id] ?? ""));
    if (entries.some((cents) => cents === null)) return null;
    return entries.reduce<number>((sum, cents) => sum + (cents ?? 0), 0);
  }, [exactInputs, participantIds]);
  const equalPreview = useMemo(
    () => (totalCents === null ? new Map<number, number>() : splitEqualCents(totalCents, participantIds)),
    [participantIds, totalCents],
  );
  const exactIsValid =
    totalCents !== null && totalCents > 0 && exactCents === totalCents && participantIds.length > 0;
  const currentBalance = parseSignedCents(
    balances.find((balance) => balance.user_id === selectedUserId)?.balance ?? "0.00",
  ) ?? 0;

  const refreshGroupData = useCallback(async (groupId: number, userId: number) => {
    setLoadingGroup(true);
    try {
      const [nextExpenses, nextBalances] = await Promise.all([
        api.expenses(groupId, userId),
        api.balances(groupId, userId),
      ]);
      setExpenses(nextExpenses);
      setBalances(nextBalances);
      setPageError("");
    } catch (error) {
      setExpenses([]);
      setBalances([]);
      setPageError(error instanceof Error ? error.message : "โหลดข้อมูลกลุ่มไม่สำเร็จ");
    } finally {
      setLoadingGroup(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    api.users()
      .then((loadedUsers) => {
        if (!active) return;
        setUsers(loadedUsers);
        const savedId = Number(window.localStorage.getItem(STORAGE_KEY));
        setSelectedUserId(
          loadedUsers.some((user) => user.id === savedId) ? savedId : (loadedUsers[0]?.id ?? null),
        );
      })
      .catch((error: unknown) => {
        if (active) setPageError(error instanceof Error ? error.message : "โหลดรายชื่อผู้ใช้ไม่สำเร็จ");
      })
      .finally(() => {
        if (active) setLoadingUsers(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (selectedUserId === null) return;
    window.localStorage.setItem(STORAGE_KEY, String(selectedUserId));
    let active = true;
    api.groups(selectedUserId)
      .then((nextGroups) => {
        if (!active) return;
        setGroups(nextGroups);
        setLoadingGroup(nextGroups.length > 0);
        const firstGroup = nextGroups[0];
        setSelectedGroupId(firstGroup?.id ?? null);
        const memberIds = firstGroup?.members.map((member) => member.id) ?? [];
        setParticipantIds(memberIds);
        setPayerId(memberIds[0] ?? null);
        setExactInputs({});
      })
      .catch((error: unknown) => {
        if (!active) return;
        setPageError(error instanceof Error ? error.message : "โหลดกลุ่มไม่สำเร็จ");
      });
    return () => {
      active = false;
    };
  }, [selectedUserId]);

  useEffect(() => {
    if (selectedGroupId === null || selectedUserId === null) return;
    const groupId = selectedGroupId;
    const userId = selectedUserId;
    let active = true;
    async function loadGroupData() {
      try {
        const [nextExpenses, nextBalances] = await Promise.all([
          api.expenses(groupId, userId),
          api.balances(groupId, userId),
        ]);
        if (!active) return;
        setExpenses(nextExpenses);
        setBalances(nextBalances);
        setPageError("");
      } catch (error) {
        if (!active) return;
        setExpenses([]);
        setBalances([]);
        setPageError(error instanceof Error ? error.message : "โหลดข้อมูลกลุ่มไม่สำเร็จ");
      } finally {
        if (active) setLoadingGroup(false);
      }
    }
    void loadGroupData();
    return () => {
      active = false;
    };
  }, [selectedGroupId, selectedUserId]);

  const userName = useCallback(
    (userId: number) => users.find((user) => user.id === userId)?.name ?? `ผู้ใช้ ${userId}`,
    [users],
  );

  function changeGroup(groupId: number | null) {
    const members = groups.find((group) => group.id === groupId)?.members ?? [];
    const memberIds = members.map((member) => member.id);
    setSelectedGroupId(groupId);
    setLoadingGroup(groupId !== null);
    setParticipantIds(memberIds);
    setPayerId(memberIds[0] ?? null);
    setExactInputs({});
    setExpenses([]);
    setBalances([]);
    setPageError("");
  }

  function toggleParticipant(userId: number) {
    const next = participantIds.includes(userId)
      ? participantIds.filter((id) => id !== userId)
      : [...participantIds, userId];
    setParticipantIds(next);
    if (payerId === userId && !next.includes(userId)) setPayerId(next[0] ?? null);
    else if (payerId === null && next.includes(userId)) setPayerId(userId);
  }

  const canSubmit = Boolean(
    selectedGroupId !== null && selectedUserId !== null && description.trim() &&
    totalCents !== null && totalCents > 0 && payerId !== null && participantIds.length > 0 &&
    (splitType === "equal" || exactIsValid) && !submitting,
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    setNotice("");
    if (!canSubmit || selectedGroupId === null || selectedUserId === null || payerId === null || totalCents === null) {
      setFormError(splitType === "exact" ? "ตรวจสอบยอดส่วนแบ่งให้รวมเท่ากับยอดทั้งหมดก่อนบันทึก" : "กรุณากรอกข้อมูลให้ครบและถูกต้อง");
      return;
    }

    const input = splitType === "equal"
      ? {
          description: description.trim(),
          amount: centsToDecimalString(totalCents),
          paid_by: payerId,
          split_type: "equal" as const,
          user_ids: participantIds,
        }
      : {
          description: description.trim(),
          amount: centsToDecimalString(totalCents),
          paid_by: payerId,
          split_type: "exact" as const,
          shares: participantIds.map((userId) => ({
            user_id: userId,
            amount: centsToDecimalString(parseCents(exactInputs[userId] ?? "") ?? 0),
          })),
        };

    setSubmitting(true);
    try {
      await api.createExpense(selectedGroupId, selectedUserId, input);
      setDescription("");
      setAmountInput("");
      setExactInputs({});
      setNotice("บันทึกรายจ่ายเรียบร้อยแล้ว");
      await refreshGroupData(selectedGroupId, selectedUserId);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "บันทึกรายจ่ายไม่สำเร็จ");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteExpense(expense: Expense) {
    if (selectedGroupId === null || selectedUserId === null) return;
    if (!window.confirm(`ต้องการลบรายการ “${expense.description}” ใช่หรือไม่?`)) return;
    setPageError("");
    setNotice("");
    setDeletingExpenseId(expense.id);
    try {
      await api.deleteExpense(selectedGroupId, expense.id, selectedUserId);
      setNotice("ลบรายการค่าใช้จ่ายเรียบร้อยแล้ว");
      await refreshGroupData(selectedGroupId, selectedUserId);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "ลบรายการไม่สำเร็จ");
    } finally {
      setDeletingExpenseId(null);
    }
  }

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Splitbill หน้าหลัก">
          <span className="brand-mark">S</span>
          <span>split<span className="brand-accent">bill</span></span>
        </a>
        <div className="topbar-controls">
          <label className="select-control">
            <span>กำลังใช้งาน</span>
            <select
              aria-label="เลือกผู้ใช้"
              value={selectedUserId ?? ""}
              disabled={loadingUsers}
              onChange={(event) => {
                setSelectedUserId(event.target.value ? Number(event.target.value) : null);
                setLoadingGroup(true);
                setPageError("");
                setGroups([]);
                setSelectedGroupId(null);
                setExpenses([]);
                setBalances([]);
                setParticipantIds([]);
                setPayerId(null);
              }}
            >
              {loadingUsers && <option value="">กำลังโหลดผู้ใช้…</option>}
              {!loadingUsers && users.length === 0 && <option value="">ไม่พบผู้ใช้</option>}
              {users.map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}
            </select>
          </label>
          <span className="avatar">{users.find((user) => user.id === selectedUserId)?.name.slice(0, 1).toUpperCase() ?? "?"}</span>
        </div>
      </header>

      <div className="dashboard-content" id="top">
        <section className="welcome-row">
          <div>
            <p className="eyebrow">จัดการค่าใช้จ่ายร่วมกัน</p>
            <h1>สวัสดี, {userName(selectedUserId ?? 0)} <span aria-hidden="true">✦</span></h1>
            <p className="muted">ดูแลค่าใช้จ่ายของกลุ่มได้ง่าย ๆ ในที่เดียว</p>
          </div>
          <label className="group-picker">
            <span>กลุ่มของคุณ</span>
            <select
              aria-label="เลือกกลุ่ม"
              value={selectedGroupId ?? ""}
              disabled={!groups.length}
              onChange={(event) => changeGroup(event.target.value ? Number(event.target.value) : null)}
            >
              <option value="">{groups.length ? "เลือกกลุ่ม" : "ยังไม่มีกลุ่ม"}</option>
              {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
            </select>
          </label>
        </section>

        {pageError && <div className="alert alert-error" role="alert">{pageError}<button type="button" onClick={() => setPageError("")} aria-label="ปิดข้อความ">×</button></div>}
        {!loadingUsers && users.length === 0 && <div className="empty-state">ยังไม่มีผู้ใช้ในระบบ กรุณาเพิ่มผู้ใช้ก่อนเริ่มใช้งาน</div>}
        {selectedUserId !== null && groups.length === 0 && !pageError && <div className="empty-state">ผู้ใช้นี้ยังไม่ได้เป็นสมาชิกกลุ่มใด</div>}

        <section className="summary-grid" aria-label="สรุปยอดคงเหลือ">
          <article className="summary-card summary-primary">
            <div className="summary-icon">↗</div><p>ยอดสุทธิของฉัน</p>
            <strong>฿{formatCents(currentBalance)}</strong>
            <span>{currentBalance > 0 ? "คุณควรได้รับเงินคืน" : currentBalance < 0 ? "คุณยังมียอดที่ต้องจ่าย" : "ยอดของคุณลงตัวแล้ว"}</span>
          </article>
          <article className="summary-card"><div className="summary-icon icon-soft">▤</div><p>รายการในกลุ่ม</p><strong>{expenses.length}</strong><span>รายการที่ยังใช้งาน</span></article>
          <article className="summary-card"><div className="summary-icon icon-green">◎</div><p>สมาชิกในกลุ่ม</p><strong>{groupUsers.length}</strong><span>{selectedGroup?.name ?? "เลือกกลุ่มเพื่อดูสรุป"}</span></article>
        </section>

        <div className="main-grid">
          <section className="panel expense-form-panel">
            <div className="panel-heading"><div><p className="eyebrow">เพิ่มรายการใหม่</p><h2>บันทึกค่าใช้จ่าย</h2></div><span className="heading-icon">＋</span></div>
            <form onSubmit={handleSubmit}>
              <label className="field">รายละเอียด
                <input aria-label="รายละเอียด" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="เช่น ค่าอาหารเย็น" />
              </label>
              <div className="form-row">
                <label className="field">ยอดรวมเป็นบาท
                  <span className="amount-input">฿<input aria-label="ยอดรวมเป็นบาท" inputMode="decimal" value={amountInput} onChange={(event) => setAmountInput(event.target.value)} placeholder="0.00" /></span>
                  {amountInput && totalCents === null && <small className="field-error">กรอกจำนวนเงินไม่เกิน 2 ตำแหน่งทศนิยม</small>}
                </label>
                <label className="field">ผู้จ่าย
                  <select aria-label="ผู้จ่าย" value={payerId ?? ""} onChange={(event) => setPayerId(event.target.value ? Number(event.target.value) : null)} disabled={!groupUsers.length}>
                    {groupUsers.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
                  </select>
                </label>
              </div>
              <fieldset className="field participant-field">
                <legend>แบ่งให้ใครบ้าง</legend>
                <div className="participants">
                  {groupUsers.map((member) => (
                    <label className="participant" key={member.id}>
                      <input type="checkbox" checked={participantIds.includes(member.id)} onChange={() => toggleParticipant(member.id)} />
                      <span className="checkmark">✓</span>{member.name}
                    </label>
                  ))}
                </div>
              </fieldset>
              <div className="field">
                <span>วิธีแบ่ง</span>
                <div className="segmented">
                  <button type="button" className={`segment ${splitType === "equal" ? "active" : ""}`} onClick={() => setSplitType("equal")}>หารเท่ากัน</button>
                  <button type="button" className={`segment ${splitType === "exact" ? "active" : ""}`} onClick={() => setSplitType("exact")}>ระบุยอดเอง</button>
                </div>
              </div>
              <div className="preview-box">
                <div className="preview-title"><strong>ตัวอย่างส่วนแบ่ง</strong><span>{splitType === "equal" ? "หารเท่ากัน" : "ระบุยอด"}</span></div>
                {!participantIds.length && <p className="muted preview-empty">เลือกสมาชิกอย่างน้อยหนึ่งคน</p>}
                {participantIds.map((id, index) => {
                  const cents = splitType === "equal" ? equalPreview.get(id) : parseCents(exactInputs[id] ?? "");
                  return (
                    <div className="preview-line" key={id}>
                      <span>{userName(id)}{payerId === id && <em>ผู้จ่าย</em>}</span>
                      {splitType === "equal" ? <strong>{cents === undefined || cents === null ? "—" : formatCents(cents)}</strong> : (
                        <label className="exact-input"><span>฿</span><input aria-label={`ยอดส่วนแบ่งของ ${userName(id)}`} inputMode="decimal" value={exactInputs[id] ?? ""} onChange={(event) => setExactInputs((current) => ({ ...current, [id]: event.target.value }))} placeholder="0.00" /></label>
                      )}
                      {splitType === "exact" && cents === null && exactInputs[id] && <small className="field-error">ยอดไม่ถูกต้อง</small>}
                      <span className="preview-index">{index + 1}</span>
                    </div>
                  );
                })}
                {splitType === "exact" && participantIds.length > 0 && (
                  <div className={`exact-total ${exactIsValid ? "valid" : "invalid"}`}>
                    <span>รวมส่วนแบ่ง {exactCents === null ? "—" : formatCents(exactCents)}</span>
                    <span>{exactIsValid ? "ยอดตรงกัน ✓" : `ยอดทั้งหมด ${totalCents === null ? "—" : formatCents(totalCents)}`}</span>
                  </div>
                )}
              </div>
              {formError && <div className="alert alert-error form-alert" role="alert">{formError}</div>}
              {notice && <div className="alert alert-success" role="status">{notice}</div>}
              <button className="submit-button" type="submit" disabled={!canSubmit}>{submitting ? "กำลังบันทึก…" : "บันทึกค่าใช้จ่าย　→"}</button>
            </form>
          </section>

          <section className="panel balances-panel">
            <div className="panel-heading"><div><p className="eyebrow">ภาพรวมกลุ่ม</p><h2>ยอดคงเหลือ</h2></div><span className="heading-icon balance-heading-icon">◎</span></div>
            {loadingGroup ? <p className="muted">กำลังโหลด…</p> : balances.length === 0 ? <p className="muted">ยังไม่มีข้อมูลยอดคงเหลือ</p> : (
              <div className="balance-list">
                {balances.map((item) => {
                  const cents = parseSignedCents(item.balance) ?? 0;
                  return <div className="balance-item" key={item.user_id}><span className="balance-avatar">{userName(item.user_id).slice(0, 1).toUpperCase()}</span><div className="balance-person"><strong>{userName(item.user_id)}</strong><small>{cents > 0 ? "ควรได้รับเงิน" : cents < 0 ? "มียอดต้องจ่าย" : "ลงตัวแล้ว"}</small></div><strong className={cents > 0 ? "positive" : cents < 0 ? "negative" : "neutral"}>{cents > 0 ? "+" : cents < 0 ? "−" : ""}฿{formatCents(Math.abs(cents))}</strong></div>;
                })}
              </div>
            )}
            <div className="balance-note"><span>ⓘ</span>ยอดบวกคือเงินที่ควรได้รับ ยอดลบคือเงินที่ต้องจ่าย</div>
          </section>
        </div>

        <section className="panel expenses-panel">
          <div className="panel-heading expense-list-heading"><div><p className="eyebrow">ความเคลื่อนไหว</p><h2>ค่าใช้จ่ายล่าสุด</h2></div><span className="list-count">{expenses.length} รายการ</span></div>
          {loadingGroup ? <p className="muted">กำลังโหลดรายการ…</p> : expenses.length === 0 ? <div className="empty-list"><span>▤</span><strong>ยังไม่มีค่าใช้จ่าย</strong><p>เพิ่มรายการแรกของกลุ่มได้จากแบบฟอร์มด้านบน</p></div> : (
            <div className="expense-list">
              {expenses.map((expense) => {
                const myShare = expense.shares.find((share) => share.user_id === selectedUserId);
                const isPayer = expense.paid_by === selectedUserId;
                const shareCents = myShare ? parseCents(myShare.share_amount) ?? 0 : 0;
                return <article className="expense-row" key={expense.id}><span className="expense-icon">▧</span><div className="expense-description"><strong>{expense.description}</strong><small>{userName(expense.paid_by)} จ่าย · {expense.split_type === "equal" ? "หารเท่ากัน" : "ระบุยอด"}</small></div><div className="expense-status"><span className={`status-pill ${isPayer ? "status-receive" : "status-owe"}`}>{isPayer ? "สำรองจ่าย · ควรได้รับคืน" : "มีส่วนรับผิดชอบ"}</span>{myShare && <small>ส่วนแบ่งของฉัน ฿{formatCents(shareCents)}</small>}</div><strong className="expense-total">฿{formatApiMoney(expense.amount)}</strong>{isPayer && <button className="delete-expense-button" type="button" aria-label={`ลบรายการ ${expense.description}`} disabled={deletingExpenseId !== null} onClick={() => void handleDeleteExpense(expense)}>{deletingExpenseId === expense.id ? "กำลังลบ…" : "ลบ"}</button>}</article>;
              })}
            </div>
          )}
        </section>
        <footer className="footer-note">ทำให้การหารบิลเป็นเรื่องง่าย <span>♥</span></footer>
      </div>
    </main>
  );
}