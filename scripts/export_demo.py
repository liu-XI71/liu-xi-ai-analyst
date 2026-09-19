"""Build honest static snapshots from the same deterministic business engine."""
from pathlib import Path
import json,sys
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import engine,reports
from app.config import ROOT,VERSION

def main():
    engine.initialize()
    dest=ROOT/'web'/'demo';dest.mkdir(parents=True,exist_ok=True)
    def save(name,value): (dest/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    save('catalog.json',{'domains':engine.catalog(),'model':{'configured':False,'mode':'demo','model':'gpt-5-mini','provider':'OpenAI Responses API'},'version':VERSION,'data_notice':'固定种子合成数据；当前为静态演示快照，没有调用大模型。'})
    for domain,task,question in [('growth','diagnose','最近两个成熟队列的次7日内留存为何下降？'),('repurchase','segment','在200元触达预算下，哪些客户值得优先召回并设置留出组？')]:
        request={'question':question,'domain':domain,'task':task,'mode':'demo'}
        result=engine.analyze_domain(request)
        result.update(domain=domain,mode='demo',request=request,static_snapshot=True,created_at=datetime.now(timezone.utc).isoformat())
        result['trace']=[{'tool':'static_snapshot','status':'completed','description':'由同一Python业务引擎生成的固定演示快照，未执行当前自由输入问题，未调用模型。'}]+result.get('trace',[])
        save(f'{domain}.json',result)
        (dest/f'{domain}-report.html').write_text(reports.html_report(result))
        (dest/f'{domain}-report.md').write_text(reports.markdown_report(result))
    source=ROOT/'evals'/'results.json'
    save('evaluations.json',engine.evaluation_summary())
    print('Exported 2 deterministic snapshots, 4 reports, catalog and evaluation summary.')
if __name__=='__main__':main()
