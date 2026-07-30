from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from opencex_settlement.orders import NCOrder
from opencex_settlement.settlement import SettlementService

class SettlementPlanView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        d = request.data
        try:
            order = NCOrder(maker=d["maker"], sell_token=d["sell_token"], buy_token=d["buy_token"],
                sell_amount=str(d["sell_amount"]), buy_amount=str(d["buy_amount"]),
                chain_id=int(d["chain_id"]), nonce=int(d["nonce"]), expiry=int(d["expiry"]),
                salt=str(d.get("salt", "0")))
            plan = SettlementService().build_plan(order, d["signature"])
            return Response({"mode": plan.mode, "chain_id": plan.chain_id, "tx": plan.tx,
                             "verifying_contract": plan.verifying_contract, "notes": plan.notes})
        except (KeyError, ValueError) as e:
            return Response({"error": str(e)}, status=400)

class AAUserOpView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        from opencex_aa.userop import UserOpBuilder
        d = request.data; chain_id = int(d.get("chain_id", 1))
        sender = d.get("sender") or d.get("account")
        if not sender: return Response({"error": "sender required"}, status=400)
        b = UserOpBuilder(chain_id=chain_id, account_address=sender)
        if d.get("tx"):
            uo = b.build_from_settlement_tx(d["tx"], nonce=int(d.get("nonce", 0)))
        else:
            uo = b.build_execute(d.get("to", "0x"), d.get("data", "0x"), int(d.get("value", 0)), int(d.get("nonce", 0)))
        return Response({"userOp": uo.to_rpc(), "entryPoint": b.entry_point, "chain_id": chain_id})
