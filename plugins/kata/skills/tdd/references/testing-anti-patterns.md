# テストのアンチパターン

**読むタイミング:** モックを追加するとき、テストユーティリティを追加するとき、プロダクションクラスにテスト専用のメソッドを足したくなったとき。

## 共通原則

モックの役目は依存を切り離すことまでである。モック自体がどう振る舞ったかにテストの関心が向いた時点で、そのテストは対象コードについて何も語らなくなる。

## アンチパターン 1: モックの挙動をテストする

モック要素へのアサーションが確かめているのは「モックが差し込まれたか」だけで、対象の挙動は何も保証しない。モックを外した瞬間に無意味になるテストである。

```typescript
// Bad: モックの存在確認にすぎない
test("通知バナーが表示される", () => {
  render(<Page />);
  expect(screen.getByTestId("banner-mock")).toBeInTheDocument();
});

// Good: モックせずに、実際に見える挙動を検証する
test("通知バナーが表示される", () => {
  render(<Page />);
  expect(screen.getByRole("alert")).toBeInTheDocument();
});
```

切り分けのためにどうしてもモックが必要な場合は、モック要素へのアサーションをやめ、モックの有無に関係なく成立する Page 側の挙動だけを検証する。

## アンチパターン 2: プロダクションクラスにテスト専用メソッドを足す

テストからしか呼ばれないメソッドを本番クラスに置くと、テストの都合が本番コードに漏れ出し、誤って本番経路から呼ばれる危険も生む。YAGNI にも反する。

```typescript
// Bad: 本番では誰も呼ばないメソッドが本番クラスにある
class UserSession {
  async destroyForTest() { await this.workspace?.tearDown(); }
}

// Good: 後片付けの責務はテストユーティリティ（test-utils/）側に置く
export async function cleanupSession(session: UserSession) {
  const workspace = session.getWorkspaceInfo();
  if (workspace) await workspaceManager.tearDown(workspace.id);
}
```

メソッドを追加する前に「これはテストからしか呼ばれないのでは」と自問し、そうであればテストユーティリティに置く。

## アンチパターン 3: 依存関係を理解せずにモックする

「念のため」のモックは、テストが依存していた副作用ごと消してしまう。まずモックなしで実行して何が起きるかを観察し、必要最小限だけをモックする。

```typescript
// Bad: syncCatalog の設定書き込みごと消え、重複検知が働かなくなる
vi.mock("ServerCatalog", () => ({
  syncCatalog: vi.fn().mockResolvedValue(undefined),
}));
await registerServer(config);
await registerServer(config); // 例外になるはずが、通ってしまう

// Good: 遅い外部呼び出しだけをモックし、副作用は本物のまま残す
vi.mock("RemoteServerClient");
await registerServer(config); // 設定は実際に書き込まれる
await registerServer(config); // 重複検知が働く
```

モックする前に対象メソッドの副作用を洗い出し、テストがその副作用に依存していないことを確認する。

## クイックリファレンス

| アンチパターン | 対処 |
|---|---|
| モック要素へのアサーション | 実コンポーネントを検証するか、モックを外す |
| プロダクションクラスへのテスト専用メソッド | テストユーティリティ側に移す |
| 理解しないままのモック | 副作用を洗い出してから、最小限だけモックする |
