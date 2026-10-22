# Gmail OAuth setup

ApplyPilot includes the desktop OAuth connection flow, read-only Gmail sync and optional sending. A Google OAuth client must belong to a configured Google project. A ChatGPT Gmail connection cannot be exported into this application.

1. Follow Google's [Gmail Python quickstart setup](https://developers.google.com/workspace/gmail/api/quickstart/python): create/select a project, enable Gmail API and configure the consent screen.
2. Configure the consent audience for your intended users. In a testing project, add your Gmail account as a test user where Google requires it.
3. Create an OAuth client with application type **Desktop app**, and download its JSON configuration.
4. In ApplyPilot's **Inbox**, choose **Google client JSON**. The configuration goes into the Windows credential vault; do not commit it to GitHub.
5. Leave **Allow sending** unchecked for read-only tracking. Check it only if you want to send manually approved messages from the app.
6. Click **Connect Google**. Sign in and complete consent in the browser. The app opens an ephemeral loopback callback on 127.0.0.1 for this flow, with a three-minute timeout.
7. After successful connection, the app retrieves the authenticated account address. Click **Sync**. Optional five-minute sync can be enabled while the app stays open.
8. To remove access, use **Disconnect** and/or remove ApplyPilot in your Google account's third-party access settings. Changing granted scopes or an expired consent may require reconnection.

The developer has not connected your Gmail account to this installed app or tested live consent with your client registration. An OAuth library/import test or mocked API test is not equivalent to a live inbox test.

Tokens and client configuration stay in the OS credential store. Sending uses the authenticated Gmail address and requires the optional Gmail send scope. Read access does not silently grant sending. Email sync stores matched message bodies locally, so protect your Windows account and storage.

No billing account or paid model is configured by ApplyPilot. OAuth project policies, API availability and quotas remain controlled by Google. Do not enter your ordinary Gmail password into ApplyPilot.
