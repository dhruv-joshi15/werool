import { chromium } from '@playwright/test'
import { writeFile } from 'node:fs/promises'
const browser=await chromium.launch({headless:true})
try{
 const page=await browser.newPage()
 for(const dataset of ['FUELHH','WINDFOR']){
  const url=`https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/${dataset}/stream`
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:45000})
  await page.getByText('publishDateTimeFrom',{exact:false}).first().waitFor({timeout:30000}).catch(()=>{})
  const body=await page.locator('body').innerText()
  await writeFile(`/tmp/elexon-${dataset}-documentation.txt`,body)
  console.log(`\nSOURCE ${url}\n${body.slice(-24000)}`)
 }
 const probes=[]
 for(const [dataset,from,to] of [['WINDFOR','2026-01-15T00:00:00Z','2026-01-15T12:00:00Z'],['FUELHH','2026-02-01T00:00:00Z','2026-02-02T00:00:00Z']]){
  const url=`https://data.elexon.co.uk/bmrs/api/v1/datasets/${dataset}/stream?publishDateTimeFrom=${encodeURIComponent(from)}&publishDateTimeTo=${encodeURIComponent(to)}`
  const response=await page.request.get(url,{timeout:45000})
  if(!response.ok())throw new Error(`${dataset}: HTTP ${response.status()}`)
  const all=await response.json();if(!Array.isArray(all))throw new Error('Expected a JSON array')
  const rows=all.filter(r=>dataset!=='FUELHH'||r.fuelType==='WIND')
  if(!rows.every(r=>r.publishTime>=from&&r.publishTime<=to))throw new Error('Publication filter not respected')
  const targets=[...new Set(rows.map(r=>r.startTime))].sort()
  const publications=[...new Set(rows.map(r=>r.publishTime))].sort()
  const spacing=[...new Set(targets.slice(1).map((t,i)=>(new Date(t)-new Date(targets[i]))/60000))]
  probes.push({dataset,url,status:response.status(),total_rows:all.length,wind_rows:rows.length,publications:publications.length,first_target:targets[0],last_target:targets.at(-1),target_spacing_minutes:spacing,fields:Object.keys(rows[0]||{})})
 }
 await writeFile(new URL('../../docs/live-source-probes.json',import.meta.url),JSON.stringify(probes,null,2)+'\n')
 console.log('LIVE PROBES '+JSON.stringify(probes,null,2))
}finally{await browser.close()}
