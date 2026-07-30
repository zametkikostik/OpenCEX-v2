export type QuoteResult = {
  buy_amount?: string;
  sell_amount?: string;
  price?: string;
  needs_allowance?: boolean;
  allowance_spender?: string;
  sell_token?: string;
  buy_token?: string;
  transaction?: { to: string; data: string; value?: string | number; gas?: string | number; chainId?: number };
  sources?: { name: string; proportion?: number }[];
  error?: string;
};

export class OpenCEXApi {
  constructor(public baseUrl: string, public token?: string) {}

  private headers(): HeadersInit {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (this.token) h["Authorization"] = `Bearer ${this.token}`;
    return h;
  }

  async registerSession(mode: string, address: string, chainId: number) {
    try {
      await fetch(`${this.baseUrl}/wallet/session/`, {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({ mode, address, chain_id: chainId }),
      });
    } catch { /* optional */ }
  }

  async getNcQuote(params: {
    chainId: number; sell: string; buy: string; sellAmount: string; taker: string;
  }): Promise<QuoteResult> {
    let res = await fetch(`${this.baseUrl}/wallet/swap/nc/`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({
        chain_id: params.chainId,
        sell_token: params.sell,
        buy_token: params.buy,
        sell_amount: params.sellAmount,
        taker: params.taker,
      }),
    });
    if (!res.ok) {
      res = await fetch(`${this.baseUrl}/swap/quote/`, {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({
          chain_id: params.chainId,
          sell: params.sell,
          buy: params.buy,
          amount: params.sellAmount,
          taker: params.taker,
        }),
      });
    }
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || JSON.stringify(data));
    return data as QuoteResult;
  }
}
