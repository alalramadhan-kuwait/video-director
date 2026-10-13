"""The only path to paid voice generation.

Enforced here (in code):
  * off unless VIDEO_DIRECTOR_PAID_ENABLED=1 (or enabled=True is passed explicitly);
  * needs an approval created for exactly this plan (hash recomputed from the plan's content);
  * an approval is single-use and expires; it caps the units it may spend;
  * the project budget must cover the plan;
  * only 'new' items are generated; reuse/review/blocked items never are;
  * every provider call happens at most once per item — no automatic retries; the first failure stops the run;
  * every result is stored as an immutable candidate take; nothing approved is ever touched.
Not enforceable in code (see Phase 0.5): a session whose environment injects the API key could call the provider
directly. That is closed by removing the key from development environments.
"""
from __future__ import annotations
import os, time
from .plan import plan_hash
from .takes import TakeStore

_GATEWAY = object()          # capability token: paid providers refuse calls that don't carry it


class PaidCallRefused(Exception):
    pass


class ElevenLabsProvider:
    """Builds the same request tts_eleven.py sends; the HTTP transport is injected (a mock in all tests)."""
    paid = True
    unit = 'characters'
    API = 'https://api.elevenlabs.io'

    def __init__(self, transport):
        self.transport = transport

    def request_for(self, req: dict) -> dict:
        return {'method': 'POST', 'url': f"{self.API}/v1/text-to-speech/{req['voice_id']}",
                'query': {'output_format': req['output_format']},
                'json': {'text': req['provider_input'], 'model_id': req['model'],
                         'voice_settings': req['settings'], 'seed': req['seed']}}

    def units(self, req: dict) -> int:
        return len(req['provider_input'])

    def synthesize(self, req: dict, _caller=None) -> bytes:
        if _caller is not _GATEWAY:
            raise PaidCallRefused('paid providers can only be called by the gateway')
        return self.transport(self.request_for(req))


class PaidGateway:
    def __init__(self, ledger, store: TakeStore, providers: dict, enabled: bool | None = None):
        self.ledger, self.store, self.providers = ledger, store, providers
        self.enabled = (os.environ.get('VIDEO_DIRECTOR_PAID_ENABLED') == '1') if enabled is None else enabled

    def approve(self, plan: dict, by: str, ttl_s=24 * 3600) -> str:
        """Owner action: approve exactly this plan, capped at its own total."""
        if plan_hash(plan) != plan['hash']:
            raise PaidCallRefused('plan content does not match its hash')
        return self.ledger.create_approval(plan['hash'], plan['project'], plan['provider'], plan['chars_total'], by, ttl_s)

    def run(self, plan: dict, approval_id: str, actor='gateway') -> dict:
        proj, prov = plan['project'], plan['provider']
        def refuse(why):
            self.ledger.audit(actor, 'paid_refused', proj, reason=why, approval=approval_id)
            raise PaidCallRefused(why)
        if not self.enabled:
            refuse('paid generation is disabled (VIDEO_DIRECTOR_PAID_ENABLED is not 1)')
        provider = self.providers.get(prov)
        if provider is None or not getattr(provider, 'paid', False):
            refuse(f'no paid provider registered for {prov}')
        if plan_hash(plan) != plan['hash']:
            refuse('plan content does not match its hash')
        ap = self.ledger.approval(approval_id)
        if ap is None:
            refuse('unknown approval')
        if ap['plan_hash'] != plan['hash']:
            refuse('approval belongs to a different plan')
        if ap['used'] is not None:
            refuse('approval already used')
        if time.time() > ap['expires']:
            refuse('approval expired')
        new = [i for i in plan['items'] if i['action'] == 'new']
        units = sum(provider.units(i['request']) for i in new)
        if units != plan['chars_total']:
            refuse('plan total does not match its items')
        if units > ap['max_units']:
            refuse('plan exceeds the approved amount')
        remaining = self.ledger.remaining(proj, prov)
        if remaining is None:
            refuse('no budget set for this project and provider')
        if units > remaining:
            refuse(f'budget too small: needs {units}, {remaining} left')
        for i in new:                                    # never pay for something that already exists
            if self.store.get(i['take_key']) is not None:
                refuse(f"{i['line']}: a take with this exact request already exists")
        if not self.ledger.consume_approval(approval_id):
            refuse('approval already used')

        report = {'generated': [], 'failed': None, 'units': 0}
        self.ledger.audit(actor, 'paid_run_start', proj, approval=approval_id, items=len(new), units=units)
        for i in new:
            try:
                audio = provider.synthesize(i['request'], _caller=_GATEWAY)      # exactly one attempt
            except Exception as e:                                               # no retry, stop the run
                report['failed'] = {'line': i['line'], 'error': f'{type(e).__name__}: {e}'}
                self.ledger.audit(actor, 'paid_item_failed', proj, line=i['line'], error=str(e))
                break
            u = provider.units(i['request'])
            self.ledger.record_spend(proj, prov, u, provider.unit, plan['hash'], i['take_key'], note=i['line'])
            key = self.store.put(i['request'], audio, ext='mp3', status='candidate', by='gateway',
                                 meta={'line': i['line'], 'plan': plan['hash'], 'approval': approval_id,
                                       'library_version': plan['library_version']})
            report['generated'].append({'line': i['line'], 'take': key, 'units': u})
            report['units'] += u
        self.ledger.audit(actor, 'paid_run_end', proj, approval=approval_id, **{k: report[k] for k in ('units', 'failed')})
        return report
