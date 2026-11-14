import {test,expect} from '@playwright/test';
import {choose} from './helpers';
test.use({baseURL:'http://127.0.0.1:4194'});
test('audit final: same-centre wrong-calendar result is accepted',async({page,request})=>{
 const result=await(await request.get('http://127.0.0.1:4193/data/results/nile_delta_ndvi.json')).json();
 const id='aoi_1234567890abcdef';
 await page.route('**/api/jobs**',async route=>{
  if(route.request().url().endsWith('/result'))return route.fulfill({json:result});
  const payload=route.request().postDataJSON();
  return route.fulfill({json:{job_id:id,status:'completed',stage:null,request:{...payload,allow_marginal:false,min_pixel_presence:0.8,processing_version:'1'},nasa_task_id:null,error:null,retryable:false,result_file:`/api/jobs/${id}/result`,created_at:'2026-11-14T00:00:00Z',updated_at:'2026-11-14T00:00:00Z'}});
 });
 await page.goto('/');await choose(page,String(result.metadata.lat),String(result.metadata.lon));
 await page.getByText('Boundary & analysis period',{exact:true}).click();
 const start=page.getByRole('combobox',{name:'Start date',exact:true});await start.fill('February 1, 2002');await start.press('Tab');
 await page.getByRole('button',{name:'Analyze area',exact:true}).click();
 await expect(page.getByText('5.727e-18',{exact:true})).toBeVisible();
 await expect(page.locator('.results-panel [role=alert]')).toHaveCount(0);
});
