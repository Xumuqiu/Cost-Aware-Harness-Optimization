"""Published token accounting, including approximate harness text allocation."""
import hashlib
import json
import re
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PRICES = json.loads((ROOT/'tua/pricing/prices.json').read_text())['models']
spec = importlib.util.spec_from_file_location('tua_utils', ROOT/'src/minisweagent/agents/utils/tua_utils.py')
U = importlib.util.module_from_spec(spec)
spec.loader.exec_module(U)
base_initial = {}

def text(m):
    c=m.get('content','')
    if isinstance(c,str): return c
    if isinstance(c,list): return '\n'.join(b.get('text','') for b in c if isinstance(b,dict))
    return ''


def overhead_chars(m):
    c=text(m)
    if (m.get('extra') or {}).get('harness') or c.startswith('Your submission was NOT accepted yet.'):
        return len(c)
    if c.startswith(('Your last response contained no valid bash tool call','Your previous response reached the output token limit')):
        return len(c)
    return sum(len(x) for x in re.findall(r'<harness_note>[\s\S]*?</harness_note>|\[harness:[^\]]*\]',c))


def parse(path, group, source):
    d=json.loads(path.read_text());task=d['task_name'].split('/')[-1]
    p=path.parent/'agent/mini-swe-agent.trajectory.json'
    t=json.loads(p.read_text()) if p.exists() else {}
    msgs=t.get('messages',[]);config=t.get('info',{}).get('config',{})
    ac=config.get('agent',{});price=PRICES['deepseek/deepseek-v4.1-flash-1017' if group=='DS-original' else 'qwen/qwen3.7-flash']
    prompt=cached=output=calls=0;h_tok=h_cost=h_low=h_high=0.0
    # Positive increase in initial templates relative to A0; task text cancels by using the same task.
    static=max(0,sum(len(text(m)) for m in msgs[:2])-base_initial.get(task,0)) if group in ['A5','Q','H'] else 0
    for i,m in enumerate(msgs):
        usage=((m.get('extra') or {}).get('response') or {}).get('usage') or {}
        if not usage:continue
        pi=usage.get('prompt_tokens') or 0;ca=(usage.get('prompt_tokens_details') or {}).get('cached_tokens') or 0;co=usage.get('completion_tokens') or 0
        assert 0 <= ca <= pi
        prompt+=pi;cached+=ca;output+=co;calls+=1
        if group in ['DS-original','B0-hist','A0']:continue
        view=msgs[:i]
        if ac.get('observation_hygiene'):
            view=U.compact_messages(view,ac.get('compact_keep_last',8),ac.get('compact_head_chars',400))
        chars=static+sum(overhead_chars(x) for x in view)
        ht=min(pi,chars/4)
        ratio=ca/pi if pi else 0
        h_tok+=ht
        h_cost+=ht*((1-ratio)*price['input']+ratio*price['cache_read'])/1e6
        h_low+=min(pi,chars/5)*price['cache_read']/1e6
        h_high+=min(pi,chars/3)*price['input']/1e6
    reward=((d.get('verifier_result') or {}).get('rewards') or {}).get('reward',0)
    reward=0 if reward is None else float(reward)
    total=((prompt-cached)*price['input']+cached*price['cache_read']+output*price['output'])/1e6
    info=t.get('info',{});exit_status=info.get('exit_status') or next((m.get('extra',{}).get('exit_status','') for m in reversed(msgs) if m.get('role')=='exit'),'')
    return dict(config=group,task=task,reward=reward,full_pass=reward==1,input_tokens=prompt,cached_tokens=cached,output_tokens=output,calls=calls,
                fixed_cost_usd=total,harness_tokens_est=h_tok,harness_cost_est=h_cost,harness_cost_low=h_low,harness_cost_high=h_high,
                inference_tokens_residual=prompt+output-h_tok,inference_cost_residual=total-h_cost,
                exception=(d.get('exception_info') or {}).get('exception_type',''),exit_status=exit_status,source=source,
                result_path=str(path),trajectory_path=str(p) if p.exists() else '',sha256=hashlib.sha256(path.read_bytes()).hexdigest())
