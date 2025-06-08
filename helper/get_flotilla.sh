#!/bin/bash
curdir=$(realpath $(dirname $0))
cache_dir="${curdir}/../cache"
json="latest_flotilla.json"
full_path_json="${cache_dir}/${json}"

if [ $(find ${cache_dir} -type f -name "${json}" -newermt '-15 seconds' | wc -l) = "1" ]
then
	echo "data already fetched"
	exit 1
fi
echo fetching

curl 'https://flotilla-orpin.vercel.app/api/vessel?start=2025-05-31&mmsis=232057367' --compressed -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) Gecko/20100101 Firefox/138.0' -H 'Accept: */*' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: https://flotilla-orpin.vercel.app/' -H 'Connection: keep-alive' -H 'Cookie: _vcrcs=1.1749397785.3600.YzFmMWY5MTg5ZGJkMDllNTBjMDY5NGRmMTlkYWVmOTI=.ce36cd0f119c8cb4dead22b144e55b08' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=4' -H 'TE: trailers' > "${full_path_json}"


