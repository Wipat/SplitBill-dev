export type User = { id: number; name: string };
export type Group = { id: number; name: string; members: User[] };
export type ExpenseShare = { user_id: number; share_amount: string };
export type Expense = {
  id: number;
  group_id: number;
  description: string;
  amount: string;
  paid_by: number;
  split_type: "equal" | "exact";
  shares: ExpenseShare[];
};
export type Balance = { user_id: number; balance: string };
export type CreateExpenseInput = {
  description: string;
  amount: string;
  paid_by: number;
  split_type: "equal" | "exact";
  user_ids?: number[];
  shares?: { user_id: number; amount: string }[];
};

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function request<T>(path: string, options: RequestInit = {}, userId?: number): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (userId !== undefined) headers.set("X-User", String(userId));

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers, cache: "no-store" });
  } catch {
    throw new Error("เชื่อมต่อ API ไม่ได้ กรุณาตรวจสอบว่า backend กำลังทำงานอยู่");
  }

  if (!response.ok) {
    let message = "เกิดข้อผิดพลาดจากระบบ กรุณาลองอีกครั้ง";
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) {
        message = data.detail
          .map((item: { msg?: string }) => item.msg ?? "ข้อมูลไม่ถูกต้อง")
          .join("; ");
      }
    } catch {
      // Keep the friendly fallback when the response has no JSON body.
    }

    if (response.status === 401) message = "กรุณาเลือกผู้ใช้ก่อนดำเนินการ";
    if (response.status === 403) message = "คุณไม่มีสิทธิ์เข้าถึงกลุ่มนี้หรือดำเนินการนี้";
    if (response.status === 404) message = "ไม่พบข้อมูลที่ร้องขอ";
    if (response.status === 409) message = "คีย์คำขอซ้ำกับข้อมูลที่ต่างกัน กรุณาส่งใหม่อีกครั้ง";
    if (response.status === 422) {
      message = message.replaceAll("total", "ยอดรวม").replaceAll("share", "ส่วนแบ่ง");
    }
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  users: () => request<User[]>("/users"),
  groups: (userId: number) => request<Group[]>("/groups", {}, userId),
  group: (groupId: number, userId: number) =>
    request<Group>(`/groups/${groupId}`, {}, userId),
  expenses: (groupId: number, userId: number) =>
    request<Expense[]>(`/groups/${groupId}/expenses`, {}, userId),
  balances: (groupId: number, userId: number) =>
    request<Balance[]>(`/groups/${groupId}/balances`, {}, userId),
  createExpense: (groupId: number, userId: number, input: CreateExpenseInput) =>
    request<Expense>(
      `/groups/${groupId}/expenses`,
      {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(input),
      },
      userId,
    ),
  deleteExpense: (groupId: number, expenseId: number, userId: number) =>
    request<void>(`/groups/${groupId}/expenses/${expenseId}`, { method: "DELETE" }, userId),
};