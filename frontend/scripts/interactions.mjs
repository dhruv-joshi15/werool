import { chromium } from '@playwright/test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
const browser=await chromium.launch({headless:true})
const page=await browser.newPage({viewport:{width:1440,height:1050}})
const errors=[];page.on('pageerror',e=>errors.push(e.message))
const origin=process.argv[2]||'http://localhost:5173'
const ready=async()=>{await page.getByRole('heading',{name:'Forecast meets reality',exact:true}).waitFor();await page.getByText('period MAE',{exact:true}).waitFor()}
const nav=async(name)=>page.getByRole('navigation').getByRole('button',{name,exact:true}).click()
async function csv(button){const promise=page.waitForEvent('download');await button.click();const d=await promise;return (await readFile(await d.path(),'utf8')).trim().split('\n')}
async function close(){await page.getByRole('dialog').getByRole('button',{name:'Close details'}).click();await page.getByRole('dialog').waitFor({state:'hidden'})}
async function cards(){const names=await page.locator('.metric-grid .metric').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('aria-label')));for(const name of names){await page.getByRole('button',{name,exact:true}).click();await page.getByRole('dialog').waitFor();assert.ok(await page.getByRole('dialog').locator('.formula').textContent());await close()}}
try{
 await page.goto(origin);await ready()
 assert.ok((await page.locator('.intro-tag').textContent()).includes('HISTORICAL EVALUATION'))
 assert.ok((await page.locator('.evaluation-context').textContent()).includes('15 Jan 2026, 10:00 GMT'))
 assert.equal(await page.locator('.workspace svg').count(),0)
 await cards()
 await page.getByRole('button',{name:'Explore Root mean squared error',exact:true}).focus();await page.keyboard.press('Enter');await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');assert.equal(await page.getByRole('dialog').count(),0)
 await page.getByRole('button',{name:'How are these values aligned?'}).click();await page.getByRole('dialog').getByText('12:00–12:30',{exact:true}).waitFor();await close()
 const chart=await page.locator('.forecast-panel .recharts-wrapper').boundingBox();await page.mouse.move(chart.x+chart.width*.52,chart.y+chart.height*.43);await page.locator('.forecast-tooltip').waitFor();for(const text of ['Forecast','Actual · half-hour','Signed error','Selected publication'])assert.ok((await page.locator('.forecast-tooltip').textContent()).includes(text));await page.mouse.move(0,0)
 await page.screenshot({path:'/tmp/wind-desk-refined-desktop.png',fullPage:true})
 await page.getByRole('button',{name:'Next decision day',exact:true}).click();await page.getByText('16 Jan 2026, 10:00 GMT',{exact:false}).waitFor();await page.getByRole('button',{name:'Previous decision day',exact:true}).click();await ready()
 await page.getByRole('button',{name:'View all 24 targets',exact:true}).click();assert.equal(await page.locator('.observations-panel tbody tr').count(),24);await page.getByRole('button',{name:'Show fewer targets',exact:true}).click()
 await page.getByRole('button',{name:'Inspect 04:00 coverage and publications'}).click();await page.getByRole('heading',{name:'Publication history',exact:true}).waitFor();assert.ok((await page.getByRole('combobox',{name:'Delivery target'}).inputValue()).includes('T04:00'))
 const vintages=await csv(page.getByRole('button',{name:'Export vintages',exact:true}));assert.ok(vintages[0].includes('publish_time'));assert.ok(vintages.length>2)
 await page.getByRole('combobox',{name:'Delivery target'}).selectOption({index:2});await page.getByRole('heading',{name:'Publication history',exact:true}).waitFor()
 await nav('Decision explorer');await page.getByRole('heading',{name:'The forecast available to you'}).waitFor();assert.equal(await page.getByRole('columnheader',{name:'Actual · MW',exact:true}).count(),0)
 const hidden=await csv(page.getByRole('button',{name:'Export day',exact:true}));assert.equal(hidden.length,25);assert.ok(!hidden[0].includes('actual_mw'))
 const toggle=page.getByRole('switch',{name:'Show historical actuals'});assert.equal(await toggle.getAttribute('aria-checked'),'false');await toggle.click();await page.getByRole('heading',{name:'Forecast meets reality',exact:true}).waitFor();assert.equal(await page.getByRole('columnheader',{name:'Actual · MW',exact:true}).count(),1)
 const shown=await csv(page.getByRole('button',{name:'Export day',exact:true}));assert.ok(shown[0].includes('actual_mw'));await toggle.click();await page.getByRole('heading',{name:'The forecast available to you'}).waitFor();assert.equal(await page.getByRole('columnheader',{name:'Actual · MW',exact:true}).count(),0)
 await page.locator('#cutoff').fill('04:30');await page.getByRole('button',{name:'Apply',exact:true}).click();await page.getByText('As of 04:30',{exact:true}).waitFor();await page.getByRole('heading',{name:'The forecast available to you'}).waitFor()
 await nav('Accuracy trends');await page.getByRole('heading',{name:'Daily accuracy',exact:true}).waitFor();await cards();const period=await csv(page.getByRole('button',{name:'Export period',exact:true}));assert.equal(period.length,745);assert.ok(period[0].startsWith('decision_date,cutoff'))
 const bar=page.locator('.monthly-panel .recharts-bar-rectangle').nth(2);await bar.hover();await bar.click();await page.getByRole('heading',{name:'Forecast meets reality',exact:true}).waitFor();assert.equal(await page.locator('#decision-date').inputValue(),'2026-01-03')
 await nav('Accuracy trends');await page.getByRole('heading',{name:'Daily accuracy',exact:true}).waitFor();const bias=page.locator('.bias-panel .recharts-bar-rectangle').nth(4);await bias.hover();await bias.click();await page.getByRole('heading',{name:'Forecast meets reality',exact:true}).waitFor();assert.equal(await page.locator('#decision-date').inputValue(),'2026-01-05')
 await nav('Accuracy trends');await page.getByRole('button',{name:'Explore 2026-01-31',exact:true}).click();await page.getByRole('heading',{name:'Forecast meets reality',exact:true}).waitFor();assert.equal(await page.locator('#decision-date').inputValue(),'2026-01-31');assert.equal(await page.getByRole('button',{name:'Next decision day',exact:true}).isDisabled(),true)
 await page.getByRole('button',{name:'View publications for 00:00',exact:true}).click();await page.getByRole('heading',{name:'Publication history',exact:true}).waitFor();assert.ok((await page.getByRole('combobox',{name:'Delivery target'}).inputValue()).startsWith('2026-02-01'))
 await nav('Data & methodology');await page.getByRole('heading',{name:'Built on Elexon. Grounded in time.'}).waitFor();for(const name of ['WINDFOR','FUELHH','API docs'])assert.ok(await page.getByRole('link',{name,exact:true}).getAttribute('href'))
 await page.getByRole('button',{name:'About this dashboard'}).click();await page.getByRole('dialog').waitFor();await page.getByRole('button',{name:'Close help'}).click()
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Open navigation'}).click();await nav('Overview');await ready();await page.screenshot({path:'/tmp/wind-desk-refined-mobile.png',fullPage:true});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile overflow')
 await page.getByRole('button',{name:'Explore Evaluation coverage',exact:true}).click();await page.getByRole('dialog').waitFor();await page.screenshot({path:'/tmp/wind-desk-refined-dialog.png'});await close()
 assert.deepEqual(errors,[])
 console.log('PASS: all 8 metric cards, keyboard dialogs, alignment explanation, detailed tooltips, date arrows, 24-row expansion, coverage links, target selector, context-specific CSV exports, outcome toggle isolation, cutoff apply, MAE/bias chart navigation, daily table links, Jan 31 boundary, help, source links and mobile layout.')
}finally{await browser.close()}
