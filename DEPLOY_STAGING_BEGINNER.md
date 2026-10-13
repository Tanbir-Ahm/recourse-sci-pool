# Staging on Railway, for a first-timer (written 2026-10-13)

You are on the **Hobby plan**. Facts from Railway's own pages (checked 2026-10-13 by web search, not yet by your account): memory costs about **$10 per GB per month**, volumes **$0.15 per GB per month**, a Hobby volume can be up to **5 GB**, and the plans page allows far more memory per service than we need. Railway's private network between your services is **IPv6**, which the search service now supports (`--host ::`); it works only between services **in the same project and environment**. Where this guide describes a Railway screen from memory it says so; if a button has a different name, look for the nearest match or send me a screenshot.

## What you are building
Two things in one new Railway project called `recourse-staging`, **separate from your live site** (nothing here touches `recourse.co.in`):
1. a **copy of the website** with the new register checks (call it `staging-site`);
2. the **search service** (call it exactly `sci-search`; its name becomes part of its private address).

## Before you start (5 minutes)
- Open your **live** Railway project in another tab. You will copy two secret values from it: `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` (Variables tab of the live website service; click the eye icon to reveal, then copy). **Do not paste them anywhere except Railway's variable boxes.**
- Open https://github.com/settings/installations, find **Railway**, click **Configure**, and under "Repository access" make sure both `recourse` and `recourse-sci-pool` are allowed (or "All repositories"). If you skip this, Railway will not list them.
- Decide a secret word for the two services to share: about 40 random letters and numbers, no spaces (for example from your password manager). Call it **THE TOKEN**. Write it somewhere private.

## Step 1: make the project
1. Railway dashboard, **New Project**, then **Empty Project**.
2. Click the project name (top left) and rename it `recourse-staging`.

## Step 2: add the website copy
1. Click **+ New** (or **Create**), then **GitHub Repo**, choose **Tanbir-Ahm/recourse**.
2. Railway starts building at once, from the default branch (`main`). **Do not worry about this first build.** Click the new service box, then **Settings**.
3. Rename the service to `staging-site` (Settings, top).
4. Find **Source** (or "Branch connected to production"). Change the branch to **`register-hooks-and-overlay`**. Railway redeploys from that branch.
5. Open the **Variables** tab, click **Raw Editor**, and paste (replace the two XXXX with the real values you copied):
```
ANTHROPIC_API_KEY=XXXX
VOYAGE_API_KEY=XXXX
```
Click **Update/Save**. Railway offers to redeploy; accept. **Do not add any WhatsApp or Gupshup variables.**
6. Settings, **Networking**, **Generate Domain**. You get an address ending `.up.railway.app`. Open it after the deploy turns green (a couple of minutes). Do not attach `recourse.co.in`.

**Check:** the page opens and looks like your live site. Ask: "Can police arrest me without a warrant for cheating?" You should get a normal answer. (This tests the new code with the search tier still off.)

## Step 3: add the search service
1. In the same project, **+ New**, **GitHub Repo**, **Tanbir-Ahm/recourse-sci-pool**.
2. It will try to build from `main` and probably **fail**. That is expected. Click the service, **Settings**:
   - rename it exactly **`sci-search`**;
   - **Source**, branch: **`claude/sharp-euler-unyfv0`** (this branch has the search service; `main` does not).
3. Add a disk (called a **Volume**): right-click empty space on the project canvas (or press Ctrl+K), choose **Volume**, attach it to `sci-search`, **mount path `/data`**. [Likely: this is where the menu is.] Size: 2 GB is enough (Hobby allows up to 5 GB).
4. **Variables, Raw Editor**, paste (put THE TOKEN where shown, and the real Voyage key):
```
SCI_INDEX_DIR=/data/sci-index
SCI_INDEX_REPO=Tanbir-Ahm/recourse-sci-pool
SCI_SEARCH_TOKEN=THE TOKEN
VOYAGE_API_KEY=XXXX
PORT=8080
```
Save and accept the redeploy.
5. **Memory:** the service needs about **1.5 GB and up to 1.8 GB while starting**. Hobby allows this. If you see a memory limit setting under Settings, leave it at the maximum. [Likely: Railway bills memory used, not reserved.]
6. Click the service's **Deployments**, then the latest one, **View logs**. Wait (first start: about 30 seconds to download the index, about 40 seconds to load). You are looking for a line like:
`sci-search listening on ::8080; index 3c80a26e42, 238,762 passages`
and the deployment turning green ("Active").
7. Settings, **Networking**: make sure there is **no public domain** on this service. If there is one, remove it. This service must only be reachable from your other service.

**If it fails with "answered HTTP 403" in the logs:** GitHub refused the index download (this happened on 13 October with an earlier version). The current version downloads a plain archive of the exact commit and needs no login. If it still happens, create a GitHub token (GitHub, Settings, Developer settings, Personal access tokens, fine-grained, read-only for public repositories) and add it as a variable `GITHUB_TOKEN`.

**If it fails:** copy the last 20 lines of the logs to me. The most likely causes: out of memory (then tell me what Settings shows for memory), or a typo in a variable name.

## Step 4: connect the website copy to the search service (shadow mode)
1. Click `staging-site`, **Variables, Raw Editor**, add these three lines under the two you have (put THE TOKEN, exactly the same text as in Step 3):
```
SCI_SEARCH_URL=http://sci-search.railway.internal:8080
SCI_SEARCH_TOKEN=THE TOKEN
SCI_SEARCH_MODE=shadow
```
Save, accept the redeploy.
2. **What shadow means:** every time someone asks a question, the site answers as normal, and afterwards quietly asks the search service the same question and writes the result in the website's log. Nobody sees it.
3. Optional, **for your own test questions only on staging**, add `SCI_SHADOW_LOG_QUESTIONS=1` so the log also keeps the question words. Without it the log keeps only a scrambled fingerprint of each question.

## Step 5: test (10 minutes)
On the staging address, ask these, one after the other, and write down anything odd:
1. Can police arrest me without a warrant for cheating?
2. My cheque bounced. What can I do?
3. Can I get anticipatory bail?
4. What does Section 318 BNS say?
5. What is the punishment for theft?
6. Is Raj Deo Sharma v. State of Bihar (1999) still good law?
7. Is Bilal Ahmed Kaloo v. State of Andhra Pradesh (1997) still good law?
8. Is Mohan Lal v. State of Punjab (2018) still good law?

Expected: 1 to 5 look like your live site. 6 to 8 should say the case was (or is reported to have been) overruled, with a box called "Currency notes (checked by code, not by the model)".

Then open `staging-site`, **Deployments**, latest, **View logs**, and type `SCI_SHADOW` in the search box. You should see one long line per question you asked. **Copy those lines (or screenshot the log) and send them to me.** I will read them: do the passages fit the question, are the case names and links right, which ones are flagged.

## Step 6: the criminal exam (when you are ready, on your computer)
I will give you the exact command when you say so; it needs your computer, a copy of the staging branch, and your Anthropic key, and it costs a few dollars of credit.

## Costs to expect (Hobby)
[Likely, from Railway's published prices; not confirmed on your bill] The search service uses about 1.5 GB all day: roughly **$15 a month** in memory, plus a few cents for the disk. The staging website adds a few dollars. The Hobby plan includes some credit, so your bill may rise by about $15 to $25 a month while staging runs. To save money: when you are not testing, open the `sci-search` service, **Settings**, and remove/stop its deployment; start it again when needed (the index stays on the disk). In Railway's **Usage/Billing** settings, set a **usage alert** (and a limit if offered) so a surprise cannot grow. [Likely: these controls exist.]

## Stop or undo anything
- To stop the search tier: in `staging-site` change `SCI_SEARCH_MODE` to `off` (or delete the line).
- To turn off the register checks: add `REGISTER_HOOKS=off` to `staging-site`.
- To remove everything: delete the `recourse-staging` project. Your live project is untouched.

## When staging looks right
Tell me. The next stage is the production switch-over, which I will walk you through the same way, with `REGISTER_HOOKS=off` first. I will not merge anything into `main` without your explicit instruction.
