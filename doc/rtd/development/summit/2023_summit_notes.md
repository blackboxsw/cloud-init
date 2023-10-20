# cloud-init summit August 2023 notes
## Attendees:

The cloud-init summit had representation both in-person and remote from the following community members:



| Name              |	Company/Project/Role      | In-Person/Remote  |
| ----------------- | --------------------------- | ----------------- |
| Sally Makin       | Canonical/Server/Docs         | Remote  | 
| Alberto Contreras | Canonical/Server-CPC/SW Eng   | In Person |
| Catherine Redfield | Canonical/Server-CPC/SW Eng  | Remote |
| Calvin Mwadime    | Canonical/Server-CPC/SW Eng   | Remote |
| Brett Holman      | Canonical/Server/SW Eng       | In Person |
| Fabio Martins     | Canonical/Support Eng         | In Person |
| Kyler Horner      | Canonical/Support Eng/TAM     | In Person |
| John Chittum      | Canonical/CPC/Manager         | In Person |
| James Falcon      | Canonical/Server/SW Eng       | In Person |
| James Falcon      | Canonical/Server/SW Eng       | In Person |
| Frederick Lefebvre| Amazon                        | In Person |
| Noah Meyerhans    | Amazon                        | In Person |
| Andrew Jorgensen  | GCP/ Guest Ecosystem/StaffEng | In person and remote |
| Justin Haynes     | GCP                           | In-person |
| Guillaume Beeaudoin| Oracle/ Platform images      | In-person |
| Paul Graydon      | Oracle                        | In-person |
| Robert Schweikert | SUSE / Distinguished eng      | In-person |
| Matthew Penington | AWS / EC2 Commercial Linux/SDE | In-person |
| Dermot Bradly     | AlpineLinux maintainer        | Remote |
| Matt Chidambaram  | Cloud Migration/ DevOs SRE    | Remote |
| Mina Galić        | FreeBSD Foundation maintainer | Remote |
| Christian Ehrhardt | Canonical/Server/Manager     | Remote |
| Wei Shi           | Redhat                        | Remote |
| Yaju Cao          | Redhat                        | Remote |
| Huijuan Zhao      | Redhat                        | Remote |
| Eric Mackay       | Oracle                        | In-person |
| Rajesh Harekal    | Oracle                        | Remote |
| Deepika Rajadesingan | Oracle                     | Remote |
| Harsha Koonaparaju | Oracle                       | Remote |
| Moustafa Moustafa |  Microsoft                    | Remote |
| Lexi Neadolski    |  Microsoft                    | Remote |
| Peyton Rovertson  |  Microsoft                    | In-person |
| Nell Shamrell-Harrington |  Microsoft/Rust Foundation | In-person
|Bastian Blank     |  Amazon/Debian                | In-person |
| Kristjan Onu      |  Nation Research Council,govCanada | Remote |



Below are the running notes per session based on the scheduled talk number above:

# Day 1:

### 1. Recent Features /  Roadmap /  Q & A: Brett Holman (Canonical)
* Slides.
* Discussion.
* CVEs, code changes, new clouds added and config modules provided.
* Versioning policy: time-based versions YY.<calendar_quarter_of_release> e.g. 22.1, 22.2 etc.
* Feedback/discussions:
   * NoahM: New docs I can now quickly navigate to solutions.


### 2. Intro of Docs Person: Sally Makin(Canonical)


### 3. FreeBSD State of the Union: Mina Galic (FreeBSD Foundation)
* Talk notes: https://scratchpad.pkgbase.live/q0Ajf3LtTaqXXH0v99Sykg?view#
* At the start of this project, 130 failing tests on BSD.
* Since FreeBSD 13.2 release, unit tests are being fixed upstream.
* Biggest issues:
   * Not being able to test on your target platform has been a real challenge.
   * Trying to ensure we have fully integrated cloud-init CI within FreeBSDs test infrastructure.
* Looking to get cloud vendors to provide official FreeBSD images with cloud-init installed.
* Mina has been driving integration tests, working on LXD platform for ease of free and local integration test runs:
   * LXD virtio vsocket support complexities causing trouble for BSD due to lack of vsocket module.
   * BSD has hyperV module, but no vsocket.
   * Spent time trying to convert Hyper-V socket module to support vsocket.
* Network refactors that resulted in infiniband support for cloud-init. Tabled that effort due to lack of resources, testing and expertise.
   * What is missing from BSD for network refactor:
      * Missing a lot of IPv6 support, progress is slow but outside contributors have added a lot of functionality
* Two big issues with BSD: FHS (filesystem hierarchy standard)
   * Every Unix has its own “FHS” standard. 
   * BSD use of /run is actually written to the root filesystem (it’s not ephemeral as cloud-init treats it)
      * Need to push distro-specific treatment of ephemeral filesystem
* AIX has announced that they would like to join the cloud hype
* The hope from Mina’s work has paved enough of a path to 
* State of the FreeBSD Union


### 4. Status of cloud-init versions and support in various distribution downstreams: Chad Smith(Canonical)
* Refresh our understanding of support downstream support matrix lifetime
* Review Ubuntu, Debian, openSUSE, FreeBSD, Alpine, AmazonLinux
* Are distributions pushing updates into stable releases
   * Ubuntu pulls latest release to stable releases 20.04, 22.04, 23.04
   * Canonical provides ESM (Expanded Security Maintenance)
   * cloud-init 
* Frederick: Can cloud-init make a backwards compatibility for release
   * Define with labels whether changeset are backward compatible
* Noah cloud-init is not consistency clear whether interface changes or behavior changes so downstream consumers can better assess risk profile
   * [concern] Don’t have a defined policy for determining whether we will pull in latest cloud-init releases into stable releases on Debian/AmazonLinux
   * Frederick: Lack of a contract is what hinders us here, if we can be more strenuous for our
* James: Ubuntu tries to keep behavior consistent on stable releases, and has downstream debian/patches to hold stable behavior.
* ChrisP: Azure finds the update process valuable especially in relation to their DataSource
* Chad: This release process is a large burden on the project
* John: New features on ESM Ubuntu versions? Divergence between cloud-init versions
* Noah: AmazonLinux & Debian try to suggest to customers to migrate to newer releases that instead of trying to backport those features to stable releases
* NoahM: would it make sense to generalize SRU process more for other distros to better engage a broader group of contributors and drive quality
* James From Ubuntu perspective we have a history of finding regressions after each SRU, this may impact partners if we are requiring a vote on releases to ensure stable release updates are “approved” for various downstreams
* Noah: try leaning toward pushing some of the SRU
* JOhnC: have clouds/partners/distros publish/queue testing
* RobertS: we could ask clouds to sponsor accounts for distribution testing
   * Want to drive ability to 
* [ACTION] releases document and downstream patches we apply to
* NoahM: do you have a separate policy for how you approach those downstream patches
* [ACTION] cloud-init PRs that break compatibility add a new ‘breaking-change’ label
   * Alberto: Also in the commit message?
   * JohnC: Potential templates in commit messages indicating breaking change
   * JohnC: Example of convention: https://www.conventionalcommits.org/en/v1.0.0
* RobertS: Need more conspicuous [breaking change] in release notes for the release
   * Want this in the release changelog it raises awareness or in git commit messages as metadata
* Quotable: “You have to deal with me if you want the stuff” – RobertS
   * RobertS: can we add some prefix in commit message metadata to differentiate Bug fix from feature
   * * Multiple people preferring changelog
* SUSE patches are found here: https://build.opensuse.org/package/show/Cloud:Tools/cloud-init
* * * Is https://repology.org/project/cloud-init/versions up to date?
* [TODO] Community, Partners Clouds and Distro maintainers please update the support matrix by end of cloud-init summit with latest details of what version of cloud-init is where and whether that release receives updates


| Distribution/Release | Cloud-init version | Receives cloud-init updates |	End of Life |
| -------------------- | ------------------ | ---------------------------| ----------- |
| Ubuntu 16.04, 18.04 |  21.1-19, 23.1.2     |   CVE / Security  | Depends on ESM |
| Ubuntu 20.04, 22.04, 23.04 | latest        |  yes              | Not EOL |
| SLE 12              | 20.2                 | Only CVE fixes    | Oct 31st 2027 | 
| SLE 15              | 23.1                 |	Yes            | Jul 31st 2031 |
| openSUSE Leap       | 23.1                 |	Yes            | Not EOL |	
| openSUSE Tumbleweed | 23.1                 | Yes               | Never |
| Oracle Linux 7      | 19.4                 | CVE / Security    | Dec’24 + Depends |
| Oracle Linux 8      |	22.1               |	               | Jul’29 + | Depends |
| Oracle Linux 9      |	22.1               |	               | Jul’32 + Depends |
| RHEL 8              |	23.1               |	CVE / Security |  |
| RHEL 9              |	23.1               |	CVE / Security |  |





| Release Patch | Link Location |
| ------------- | ------------- |
| Ubuntu 20.04 |	https://github.com/canonical/cloud-init/tree/ubuntu/focal/debian/patches |
| Ubuntu 22.04 | 	https://github.com/canonical/cloud-init/tree/ubuntu/jammy/debian/patches |
| Suse Patches |	https://build.opensuse.org/package/show/Cloud:Tools/cloud-init |


## 5. Roundtable--Python version support matrix and deprecation plan: James Falcon(Canonical)
* Record current python versions under long term support by various distributions versions
* Ubuntu: LTS support matrix
* Policy for deprecation
* What keeps you on an older
* SuSE freezes once the distro hits stable 
* //OpenSUSE 15 concluded that python 3.11 and all dependencies
* ChrisP: Why do you want to update to newer python version
   * James: newer features provided
* JohnC: how to add new Python features and maintain ESM / LTS support?
* FredL/NoahM: the cost of moving to newer python versions is “beyond annoying” it would be helpful to take into account the costs of that shift to newer features as it forces downstream work
* NoahM: If there are critical security fixes added to upstream, is it possible for ease of downstream adoption of security features?
* RobertS: How do we test this across multiple versions when we end up developing w/ our local python version. This leads to gaps because we are human. Does this come down to testing to assert
   * How can we integrate unittests so that each flavor and/or distribution can be exercised everywhere to assert we don’t have regressions
* RobertS: I still pull in new major version of cloud-init into supported versions (including 3.6)
   * “I have no fear”, Update twice a year
   * It’s not possible to test everywhere, OpenStack is one of those cases
   * Customers are very helpful in that regard as they will prefer to test newer versions and collaborate with SuSE on verification
* RobertS:  potential pivot to python 3.11 in 9 months
* Mina: 3 supported BSD releases  12.4, 13.2. 11.X has been EOL for few months now 
   * Next release is 14, coming out as soon as OpenSSL integration is completed and current LLVM release 16
   * 3rd party software: all FreeBSD releases contain the same version of cloud-init. So latest cloud-init releases are published to all active supported releases
   * Also there is a quarterly release of those ports to provide “stable adopters” with only bug and security issues being fixed
   * Bleeding edge version of cloud-init is available in the form of the net/cloud-init-devel port
* ChrisP: How many distros actually pull regular new upstream cloud-init versions which may need additional testing?
   * Noah: (debian) Don’t currently regularly pull cloudinit into supported releases
   * Only backport when we need to

| Distribution/Release | python  version | End of Life | 	Does this release take upstream release |
| -------------------- | --------------- | ----------- | --------------------------------------------- |
| Ubuntu/Bionic (18.04) |	3.6             |  ~2030?     |	Security Only |
| Ubuntu/focal (20.04)  |	3.8             | ~2025       |	yes |
| Suse                  |	3.6             | ~9 months to a year |  |
| OpenSUSE 15           |	3.6 soonish 3.11|  Not EOL    | yes |
| Mariner 2             | 3.9             |  No EOL     | yes |
| RHEL 8                |	3.6             | May 2024?   |	python 38 is available but not default |
| Amazon Linux 2023     |	3.9             | ~2028 |Not systematically |



## 7. Roundtable: status of distribution downstream patches (Brett)
* [REQUEST] Looking for public download patches that partners are willing to review
* ChrisP Azure Mariner team carries downstream patches
* AmazonL has private patches may make sense to upstream it’s a TODO
* Cloud-init wants to avoid
* RobertS: 
   * Can cloud-init] documentation would be helpful to generate a list of what distributions. James: We already generate distribution support in rendered docs
   * Noah : cloud-config.tmpl does also override and filter out certain modules from
* 

## 8. Roundtable: status of testing and or publication of cloud-init in various OSes: Chad
* What gates publication of cloud-init on each distribution
* Review Ubuntu, Debian,openSUSE, FreeBSD, Alpine, RedHat if possible
* NoahM: may not be giving away that we are not running 
   * Debian: unittests run as part of the package build process
   * Existing upstream integration tests not run in debian or AmazonLinux right now
   * AmazonLinux has similar integration type tests, realistically, can/should be converted to 
   * Different framework for testing packages in the distribution in general
      * Possibly refactor of AmznLinux could be reasonable for
      * May be worthwhile investigate running integration tests with Debian and Amazonlinux 
* Chad: Better documentation would take it a long way
* ChrisP: rely on cloud-int upstream testing to get the breadth of testing on for broad features
   * Test with cloud-init upgraded in images at scale, to check for regressions
   * Looking for checkbox for release
   * NoahM: are you testing cloud-init features specifically or using existing test infra to see if you have regressions related to
* Chad: So we have people leverage existing testing as well as people testing things more pertinent to them
* Guillerme: Oracle have general infrastructure tests that watch for regressions with new cloud-init images
* Chad: We want to make it easy to let others run integration tests while also getting that feedback from other platforms. Are there any public endpoints upstream can consume?
* dermot_bradley : what about cloud providers provide a “stock metadata” that allows providers can provide emulated content to mock the IMDS
   * Robert: Once we mock IMDS, there are other platform services




## 9. Demo-- Integration testing updates for pycloudlib (James Falcon)
* Slides: Integration testing updates 
* Generalized for all clouds
* * NoahM: how do you get new version of cloud-init on the image under test
   * James: we start from a public image
      * Launch image
      * Upgrade cloud-init
      * Run cloud-init clean –logs
* Pycloudlib:
   * Most Linux distributions are supported given the ability to discover
* James:
   * Per-PR testing CI runs on Ubuntu on LXD
   * Why would CI
   * Jenkins daily runners give a healthy signal on GCE, EC2, Azure
   * For Rust project: they talked directly to github about increasing governor
   * ChrisP: Is there a mechanism to validate certain PRs on Azure
   * In Rust: Bohrs-bot in github to kick off conditional jobs
      * https://forge.rust-lang.org/infra/docs/bors.html
      * Fork of https://github.com/rust-lang/homu
* ChrisP: Is jenkins publicly accessible
   * Chad: nope security due to malicious plugins
   * Chris: We would like to trigger specific test runs on Azure 
* Ahn: do you use merge-queue? To queue CI run after Merging
* Mina: how has move from BZR -> GH changed your workflow
   * It feels like there is a stumbling block in how pull requests are being designed given that some work flows are not ideal for some teams
* James: I don’t think it’s realistic for cloud-init upstream to test all distros in our jenkins test runner
   * ChrisP what is the blocker to that: cost?
   * JohnC: Some testing accounts are tied to costs and accounts that are sponsored
   * ChrisP: if we can sort cloud accounts/costs, would that provide us with
   * JohnC: looking at our matrix, we have to understand the depth we want to the support matrix of how many instance types/sizes.
   * Discussions with cloud platforms are needed to determine what instance type/distro matrix is “good enough”
   * RobertS: this matrix only continues to grow and is not sustainable for all clouds and all distros. It’s a combinatorial problem
   * Want the ability to specialize tests to a given cloud based on where the changes are scoped (per datasource/per distro) to reduce test matrix costs and make testing sustainable
* ChrisP: if you see upstream tests, does that give you a sense of certainty that allows you to avoid certain tests
   * RobertS: I just take it and accept the work being done upstream and say thank you.
* RobertS: pycloudlib has a dependency problem that makes it hard because it pulls in all botocore azure SDK etc to support all platforms which makes it harder
   * For some projects in suse they have conditional build flags that limit/segment the dependencies to make it easier to only depend on certain SDKs
* Chad: possible to add more segmentation in tests but would be valuable
* Waldi: debian uses apache libcloud
* FrederickL: there are a number of moving pieces trying to track with the test matrix,  clouds should be best placed to define proper testing
   * Clouds should do more of the testing as they are best placed to do that testing
* JohnC: sounds like it talks around a web service that would allow for posting test results 
   * Mina: can we establish a way to trigger specific builds on Azure on a per pull request basis
* RobertS: We have OpenQA, but there’s still the issue of cost
   * If upstream works on documentation for integration testing per distribution, downstreams can consume that and try to leverage those docs to make per-distro test runs
      * If we have a 30 step procedure for how best integration test
      * Might want to solve small problem to define manual steps to enable downstreams to better integration test, allow developers to enable integration-tests on their distro/cloud rather than trying to define bigger funding/policies and public services
      * If it’s relatively easy for SUSE to kickoff and run tests, but 
* Takeaways:
   * Better docs for integration-tests to onboard other distros/clouds for testing
   * Improve visibility to upstream test status
   * MSFT or other clouds engaged in integration-testing, determine per-cloud/distro what makes sense for leveraging where partners are investing  their development time
   * Entire test matrix is likely too large for any single entity to test everything
* RobertS: “This is an fdisk problem; this is not my problem”


## 10. Security policy overview: Chad
* Upstream github pull requests that warrant security review add label “security”
* Overview for filing new security issues: https://github.com/canonical/cloud-init/security/policy
* Either 
   * 1. Send an email to cloud-init-security@lists.canonical.com reporting the security bug
   * 2. File a bug https://bugs.launchpad.net/ubuntu/+source/cloud-init/+filebug and mark it as “Private Security” 
* After the bug is received, the issue is triaged within 2 working days of being reported and a response is sent to the reporter.
* The cloud-init-security@lists.canonical.com is private. 
* Any vulnerability disclosed to the mailing list or filing a private security bug should be treated as embargoed as any affected parties coordinate a reasonable disclosure release date.of 
   * Disclosure date is based on severity the bug, affected party development time for
* If a CVE is warranted the Canonical security team will reserve a CVE id that will be represented on the bug and published bug fix
* At disclosure date, email is sent to cloud-init@lists.launchpad.net
* Review new or dropped contacts needed for security notifications?
REDACTED emails

-- 11. Demo-- Ubuntu live installer: Dan Bungert (Canonical)
* Cloud-init summit `23: Subiquity, Autoinstall, and Cloud-init
* 

-- 12. Canonical CPC, test framework John Chittum (Canonical public cloud Manager)
* Ubuntu-Build-And-Test-CloudInit-Summit.pdf
* 

-- 13. Cloud-init schema validation and validation service: Alberto Contreras (Canonical)
* cloud-init schemas
* Minimal: some distros have different schemas, how to deal with that?
* Chad: separate schema files ?
* RobertS: This is going to be an “after the fact thing”. Users are not going to use it.
* [ACTION] Print schema warnings / errors to the console / journald. More visibility.
* ChrisP, RoberS, aws: Hard-error on schema errors is very valuable.
* [ACTION]: Do not show subsequent error traces in the case of a non-valid cloud-config.
* NoahM: I want hard errors at console for schema validation problems
   * DermotBradley: some cloud providers don’t give console support by default…. So expecting the “error” output console being your primary means of communication will not help certain platforms 
   * ChrisP: customize strict failures depending on use-case and clouds
      * [ACTION] Investigate providing an option to make schema errors a hard error at system boot that is configurable by cloud/distro image creation. Imagine “error_handling” config keys.


# Main Sessions, Day 2 -- Thursday, Aug 10, 2023
## 14. cloud-init and Alpine: Dermot Bradley (AlpineLinux)
* Slides: cloud-init-and-alpine.pdf
* Discussion
* 3yrs pkg maintainer cloud-init and cloud-utils
* Musl vs glibc (developer focus is POSIX-compliance, reluctance to non-POSIX compliance) any strong non-POSIX features devs rely on make this a blocker to Alpine dev due to musl dependency
* Non systemd, busybox’s init and
* Alpine doesn’t “not like” systemd, but systemd developers don’t support alternatives to glibc so it makes systemd support tough
* Alpine not udev they use mdev….. Initframfs uses mdev, so udev support, while packaged, may cause config friction with other parse of the busybox init stack
* Sudo is packaged but not used in favor of ‘doas’ due to some of the fairly frequent security concerns w/ sudo
* Nocould-net writes to ENI and seeing secondary writes of ENI config files that don’t effectively ifdown the previous temporary interfaces
* Renderer issues w/ multi ipv4 addresses showing up in wrong net config section, likely problems with network config/internal conversion logic
* Fix hook-hotplug  to avoid hadcoding bash for the script
* Fix lock_passwd: Openssh config: password: *  behavior is difference in BSD vs Linux, special cased due to PAM enabled
   * If PAM is not enabled, * means locked
   * Alpine has PAM/kerberos/other: 
      * Alpine has to build images with PAM-enabled otherwise passwords 
* Problems:
   * Alpine has to grab latest python for edge repo. 
   * Edge repo moves to latest python 1-2 days for new python version
   * Could create a window where cloud-init could be broken
   * * Future work:
   * Alternatives to SSH: dropbear and tinySSH
   * cc_wireguard for Alpine, non-ubuntu
   * Improve console output layout to make it 80 chars wide given IPv6 output/routes line-wrap etc
   * * Tooling Dermot uses for creating images:
   * https://github.com/dermotbradley/create-alpine-disk-image 
* Questions:
   * Is it worth calling out specific distribution concerns/dependencies in cloud-init docs (mdev/busybox/non-bash/doas concerns)?
      * NoahM: do you need to make it granular per distro: POSIX/non-POSIX approaches
         * DermotBradley: may not need much in the way of docs
            * For systemd/non-systemd envs Alpine isn’t alone, Gentoo is in that, gentoo directory provides cloud-init code dropins.
            * Checked in IRC channel to get an impression from the project, didn’t get a handle on the project stance. Opinion is that maybe Alpine is the only distro using init.d
         * BrettH: there was an effort recent: Devuan to attempt to add cloud-init and they didn’t try to upstream it, COS (google) may be using openrc, carry sid?
   * How do you as Alpine maintainer track new issues/features/development needs/ongoing work?
      * prioritization is up to Dermot as maintainer
      * Alpine has official cloud-init images for AWS:
      * Tinycloud core Alpine developers use
      * [ACTION] dermot provide links to “official images” in clouds or public repository/website/service. Alpinelinux.com website and downloads
      * https://alpinelinux.org/cloud/
      * Cost prohibitive to host “official” images in multiple clouds etc
         * Some talk about making official images on GCP and other clouds
         * One person paying for all clouds.
         * NoahM: talk to Debian publishing from, AWS account is sponsored by AWS… there are similar accounts 
            * NoahM can help Dermot Bradley get in touch with right people for open source engagement to start talks about open source sponsor accounts for hosting “official images”

## 15. Documentation overhaul and policy for cloud-init (Sally Makin)
* Slides
* From Mina: I’ve seen some people complain that the style is a bit hard to read… that the fonts are too thin and light – maybe try Atkinson Hyperlegible
* Kyler just opened an issue on this docs for how arrow navigation works and ideally
* RobertS:  Cloud-init.readthedocs.io is distro agnostic, people discovering docs may get the opposite impression given canonical/ubuntu in the URL - it then others may be concerned
   * What do other distro downstreams do, reflect docs
   * Sally: readthedocs.com requires using the company name in the slug as it’s pulled from the repo. I asked RTD support if we could get rid of that, they said absolutely not :(
* Mina suggests https://cloud-init.io (+1 from Noah)
   * ACCESS




## 16. Discussion: boot speed in cloud-init: Chad, Alberto, Catherine Redfield (Canonical)
* Discussion: cloud-init boot speed
* Round table discussion points
* Concerns for group?
* RobertS: Ran time to SSH tests on SUSE years ago. GCE: 38.5s EC2: 52.2s Azure: 104s. After time to SSH, rest of come up is reasonably consistent. Does time cloud-init takes make a big difference?
* Noah: These numbers have come way down. Cloud-init is now a bigger part of it. EC2 has made amazon linux changes: IO is a really significant contributor when IO is cold. Reducing data loaded from disk helps a lot. E.g., reduce size of initrd. All modules and dependencies being loaded contributes much. 
* Meena: Firecracker is the biggest one contributing to FreeBSD
   * microVM  hypervisor: AWS open source project, EC2-specific hypervisor
   * Optimising BSD for firecracker leads to approaches that could be applicable to generic hypervisors (Colin Percival) ec2-boot-bench for getting fine-grained launch time instruments (time to network response, port 22 open etc)
* Chad: Agreement that time to SSH / network availability on first boot priority. Pets not priority
* AndrewJ: Time to SSH may not be what all users actually care about, but it's what Gartner and others measure when they compare clouds, so it matters anyway, and it's not a bad proxy measurement.
* EC2 vast majority of instances don’t reboot, they are torn down after no longer used, upgrade to new instances
* johnC: “time to workload” suggestion from some clouds, but “what workload” is the important question… hard to define beside just treating SSH
* Dermot: typically running chrony (waits til time sync) impact boot time, individual
* Meena: Some large cloud-init scenarios include reboot to ensure everything comes up
* John: In kubernetes, time to serve container is most important
* Noah: early init might not be as small as you think. Especially BIOS boot.
   * 13 CPU instruction 508 bytes of disk at the same time lots of I/Os that significantly impacts cost to boot
   * Less pronounced in UEFI
* Chad: Compression has a large effect on initrd time. Tradeoff between image size and speed. Also complexity of storage and networking stack. Can be 2+ minutes for very complex instance types. (back to slides so not taking notes on that)
* Dermot: Does Grub currently make use of any seed passed by UEFI? That would speed up initial entropy seeding.  re: stage 3 improvements
* Noah: Time spent generating SSH host keys
* Noah: can we reduce IMDS keys and limit the initial crawl footprint for init-local?
   * Can we ask for a single JSON representation of critical config data
      * Guillaume: We might not get a warm initial response but if it’s never asked it will never be put in any roadmap either.
   * CatRed: To answer your initial question, we know what minimal keys we need, 
      * To ask for individ keys, it may make sense to look at a single URL to obtain that data
      * Could we ask for “cloud-init-local” URL from IMDS to seed content
   * NoahM: Early boot keys is not necessarily cloud-init-specific so it may be easier to define a generalized “early boot config” that isn’t cloud-specific
   * NoahM: the cpu cost associated with multiple requests amortized across all of Ec2 is likely to be very high, the potential for savings is also high and therefore may be justified in order to improve boot time, improve performance, reduce costs
   * Also consider early boot keys in non-network location (e.g., smbios)
* Dermot: Also look at caching opening json schema file
* Chad/John: Avoid cost of ephemeral dhcp by keeping the IMDS data local to the instance rather than using network (also cuts down security concerns)
* Chad: Considering pre-compiled binary too, but would be a big effort/cost
* Noah: Rather than reinitialize everything, can we use a persistent process?
   * Investigated  a signal, flag condition that’d avoid loading python in later boot stages to avoid the python initialization cost
   * Noah has seen hundreds of milliseconds for python spinup
   * * Chad: Also an option to have a smaller cloud-init with reduced stages
* Biggest question around removing host key types are certain ones required for compliance? In Amazon had to re-enable older types for FIPS
* Chris: on some distros, SSH starts early and then needs to restart after SSH module. If the module moved earlier, we might be able to cut the restart
* Robert: For use cases that need large scale, you’ll probably have a minimal cloud-config, so we probably shouldn’t worry about efficiencies in the later modules
* Dan: We’ve had a few bugs around implicit ordering cycles.
* Chad: if we change/remove waiting for snap seeding, there’s no indication that cloud-init is actually waiting for snap seeding.
* Minimal cloud-init in a precompiled language
   * Nell: would definitely be interested in collaborating should Rust be pursued
* [ACTION] John: get from clouds/partners what is the minimal system/features do partners care about
   * User creation, ssh key setup, what kind of network config needed
   * E.g., smart nics or appliances or immutable apps/solutions
* Robert: Images with cloud-init vs images with ignition + afterburn. On the spot numbers for consideration:
   * Data collected on EC2 on t2.micro in us-east-1
   * Instance of SLE-Micro which uses Ignition/Afterburn
      * Startup finished in 2.860s (kernel) + 12.437s (initrd)
   * SLES 15 SP5 basically the same initrd (no ignition afterbuurn)
      * Startup finished in 2.716s (kernel) + 5.160s (initrd)
      * Cloud-init in this instance (all services per systemd-analyze) 11.143 s
         * Off this 9.248s cloud-init-local.service
* Log levels:
   * []: noted that they do find the logs saying how many bytes are read logs helpful for debugging

## 17. Demo-- instance-id in LXD: James
* Followed by roundtable: Roundtable: instance-id
* Can we determine consistent set of rules for when we get a new instance-id from clouds and what it means to cloud-init for those cases
* NoahM: if a host is rebooted and IMDS is unavailable, cloud-init seeing new instance id triggers the “re-run” behavior which is undesirable
   * If we have a way to see instance-id out of something like SMBIOS would prevent unnecessarily triggering re-run from cloud-init
* Chad: This is happening because datasource moved from DataSourceEC2 to DataSourceNone. We can likely improve this behavior as instances usually aren’t being moved between clouds
* Some clouds use regen network per boot
   * AmznLinux regenerates network every boot and doesn’t use cloud-init for that
   * Frederick: some customers felt they wanted to block IMDS access after first boot for their use case.
* Mina: any goal to make modules more idempotent
   * Chad: A good ideal and something that we can document as policy/intent for both module creation as well as ongoing module review.
   * [ACTION] followup to define policy or approach for better ensuring and reviewing idempotent PER_INSTANCE defined cc_* module runs in light of reruns will be idempotent
* Is it useful to have a separate mechanism to define a scoped id change to limit scope of the config changes cloud-init takes (network vs everything vs an individual config modules)
* 

## 18. cloud testing tools in cloud-init ecosystem: Chris Patterson/AhnVo (Microsoft)
* We all build our own tools/testing/performance/reliability
* Are there tools out there for perf and reliability that could be leveraged
   * We may all have downstream/specific tools to scrape cloud-init logs looking at cloud-init.logs to scape WARNINGS/ERRORS from logs to determine
* Azure spends a lot of time to detect errors as discovered in house to define dhclient failed to 
* If there were a repo where partners can provide regex’s for log analysis to determine failures and watch for regressions
* LISA tools do their own thing, we do our own thing
* Anh: cloud-init collect logs can we supplement or reduce the files that are being collected maybe with a manifest:
   * Chad: sounds like a good feature request.
   * [ACTION] file a bug for this feature for extending default behavior
* ChrisP: Are there scripts/checkpoints for regressions
   * RobertS: when I do cloud-init update to latest release I create new images and launch on cloud X,Y,Z uses
* ChrisP: are there plans to surface cloud-init status –format=json
   * BrettH: work in progress on warnings raised though

--19. Rotten tomatoes: what can cloud-init project do better
* Brainstorm areas for improvement, policy changes, automation, feature sets, communication changes that may help improve the cloud-init as a project and engagement from communities
* Open season for suggestions, gripes, improvements to be had.
* How should we engage the community more?
* What blocks you?
* Former IRC meetings are no longer held, having synchronous meetings wasn’t supportable and significantly useful for broad timezone support
   * Mina: ￼ that status meeting was always at a terrible time… for people with small children in Europe, anyway. 
   * * Preferred communication?
   * Noah: Mailing list
   * Robert: Mail is good. Meetings were nice but too busy and not great time to attend. Weekly summary would be nice.
   * Noah: More than just git log, but a top level summary would be best
   * Maybe weekly link list of landed PRs, GH account name
   * [ACTION] Work with NeelS(MSFT) to better define weekly digests from github and reporting to cloud-init mailing list the landed PRs and authors, maybe supplemental context
* Robert: It’d be good to better highlight the problems/actions taken for a CVE, especially when historical data is involved.
   * [ACTION] review security policy for data we release to our security partners. IF we know we are dealing with distro-specific and packaging concerns it’s best to provide that to partners during embargo time to allow them to prepare.
* NoahM: small request. Really dislike squash merge all pull requests
   * Discards what I’ve done and the way I’ve architected the cohesive changes and understand the intent. Prevents my ability in the future to understand the thought process for my changeset to bisect problems when they show up.
* Mina: [2:31 PM] Mina Galić (meena) (Guest)
   * that's sounds like what i was talking about yesterday wrt the Pull Request workflow… https://jg.gg/2018/09/29/stacked-diffs-versus-pull-requests/
   * Stacked Diffs Versus Pull Requests | Jackson Gabbard's Blog
   * A post from Jackson Gabbard on Jackson Gabbard&#039;s Blog provided by: https://jg.gg
   * [2:33 PM] Mina Galić (meena) (Guest)
   * "I'll just open more pull requests" — that's really difficult to do tho, if they build on each other.
* [ACTION] define policy or option for opting out of squash merges and what expectations there are of such Pull requests that want to avoid squash merge and put it to the mailing list:
   * Mina: if opting out of squash merges, we probably want CI to pass on each commit
   * NoahM: part of the value of preserving individ commits is that you can use git bisect to check those commits individually to assert which commit did break
      * Your individ commits shouldn’t break the code so need to understand
      * * Strong opinions of mailinglist versus discourse(forums)
   * JohnC: nice thing about discourse is digests that act like mailinglists, discourse provides opportunity to dive deeper if necessary
   * James:  appreciate the ability to subscribe to threads
   * Noah/Robert: prefer email
* RobertS: Document list of config modules per distro




## 20. ISC-dhclient deprecation status: Brett
*  REview of changes that have happened in cloud-init for DHCP support
* questions/comments:
   * RobertS: suse has interest in getting rid of the dhcpclient, file a request to make NetworkManager’s dhclient calable from the command line
* [INVESTIGATION] dermot bradley: is ipv6 support considered in this migration/deprecation????[h] 
*  NoahM: ec2 amazonlinux: talked about using a link local ipv4 addr statically, or randomly choosing the address to avoid round trip w/ dhcp server which is unnecessary
   * Ec2 doesn’t use ipv6 LL but Unique Local address
   * VPC == funny network, not proper layer2 network, don’t have to worry about address conflicts
   * BrettH: can be used as performance optimization but not cloud generic.
   * * Walkthrough of pull requests to support this feature set over the last year
* RobertS: maybe we rip all it out and farm it out to the kernel, Oracle requires network address in initrd 
* JohnC: initrd for Ubuntu is only a fallback mechanism if kernel itself does not boot, straight kernel no initrd
* ChrisP: in most cases we are doing dhcp on boot, why not have that dhcp config already in the image 
* For iSCSI solutions, initrd has to have network up to get ahold of the storage, so leverage it where necessary.
* And NetworkManager has a dhcp engine that is not exposed on the command line might be able to get solutions that provide this
* AmazonLinux: uses systemd-networkd


Wrapup/Thanks 3:15 PM Pacific Daylight Time
* Takeaways/roundtable/group retro on how the summit was organized
* Physical summit location query
   * Seattle most likely candidate for next summit
   * If Europe physical summit, may not have as much attendance from west coast clouds
   * Merging cloud-init with UDS location as a separate conference?
   *    * what could be better handled next summit:
      * Communication
      * Planning of firm talk start/stop talk times Y/N?
      * Types of talks, discussions, demos
      * Timing of talks Timezone
      * How to increase participation
      * How was remote accessibility
      * Should we open this up this event more broadly to the general community for dropins via public mailing list post/IRC post of talk times
      * YOUR_SUGGESTION_HERE
* Would Virtual conference:
   * May not get engagement
* Project improvements
   * Communication channels
   * Security publications
   * Release frequencies: ~time based quarterly
   * Release hotfixes: patch release versioning on a 23.2.X pushed to github, email sent out with the update
   *    * YOUR_IDEA_HERE
   * * Action items, investigations and followup
   * Continue to drive toward multi-distro/cloud integration-test adoption
      * Add more official docs around integration test procedure for a new platform/distro


## 21. Potential Breakout development sessions from earlier discussions
* Nells: bring RUST github workflows and policy to cloud-init
* Better enabling integration-test use in non-Ubuntu environments
   * Walk through procedure to get other distributions, drive live demo of integration testing, propose doc updates to 
* Strawman proposal for Schema warnings treated as hard errors (want configurable setting in images for certain platforms bool T/F, default False)
* Branch schema warnings emitted to console, not just logs
* [ACTION] Review and discuss policy changes  https://www.conventionalcommits.org/en/v1.0.0



Notes:
* Amzlnx : every 2 years for release, would be more likely to snapshot cloud-init upstream released
   * Some custom config modules for selinux startup and other modules that may make sense to drive some of those change
* AL2023: version repositories
   * When launching 2023 it’s pinned to a specific version of the repository
* AL1 AL2 and 2023 are different products
   * Realistically have only shipped 3 versions of cloud-init

