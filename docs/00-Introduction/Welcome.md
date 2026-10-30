# Welcome to Data Ark

*Inspired by the ancient Pharos of Alexandria—both a vital navigational aid for travelers and a beacon leading directly to the greatest repository of knowledge in the classical world. A modern, self-contained harbor for offline reference, technical guides, and preserved human knowledge.*

[Access your content](/content.html) · [Other resources](/resources.html) · [Community board](/community.html)

## What the Ark does

Data Ark is a Raspberry Pi appliance with a content SSD and its own Wi-Fi hotspot. It serves locally preserved knowledge to phones, tablets, and computers. Reading the local library does not require an account, a subscription, or an internet connection.

Connect to the DataArk Wi-Fi network and open http://192.168.4.1/ in your browser. Your device may offer a Sign in to network notification; that opens the local landing page. The notification is part of captive-portal discovery, not a request to create an account.

## What is available

The landing page lists installed collections and local map resources. Kiwix provides browser reading for ZIM archives such as Wikipedia, WikiMed, technical Q&A, and iFixit. Other formats may need their own reader. A source mentioned in the project vision is not necessarily installed on your Ark.

The Access your content page explains browser reading, original-file downloads, read-only SMB shares, anonymous read-only FTP, and direct SSD use. People with Pi accounts can also use SFTP or rsync over SSH.

## Shared access and caretaking

Reading and copying the public library are open to everyone who can reach the Ark. Downloads, removal, and reinstatement currently require the shared caretaker password. This is the existing network administration password; it is separate from a device's Wi-Fi password or Linux login.

The caretaker protects the shared copy and available storage. Removing a collection affects everyone using this Ark, so it requires confirmation. Source details remain available for supported reinstatement.

## Useful beyond reading

The Ark also brings local networking, file transfer, general Linux computing and installed tools. Some are open public services; shell and changes to shared state require authorization. See [Resources beyond the library](../10-User/Resources.md) for what exists now and what is only a possibility.

## Start here

- [User Guide](../10-User/UserGuide.md): connect, read, copy, and understand the status controls.
- [FAQ](../10-User/FAQ.md): common connection, reader, and download questions.
- [Library management](../20-Administration/Library.md): add, remove, and reinstate collections.
- [Why Data Ark?](Why.md): design goals and practical limits.

## About the content

DEJ Software creates the Data Ark software and curates references to third-party resources. We claim no ownership of those resources. Copyright, trademarks, attribution requirements and license terms remain with their respective owners.

The bootstrap kit includes software, configuration and source references; it does not bundle the referenced third-party collections. Downloads populate an individual Ark for offline use. Public accessibility does not necessarily grant permission to redistribute content. Consult each publisher’s license and individual notices before sharing copies.

Even without downloaded collections, the configured catalogue is a curated reference list to online resources. Publisher links and source details remain useful before installation and after removal; a source reference does not mean a local copy is available. Installed collections provide offline access, while online references require an internet connection.
