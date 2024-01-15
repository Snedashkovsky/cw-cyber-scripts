SELECT date,
       uniqExactIf(proof_address, proof_address != '')                    as proof_addresses,
       uniqExactIf(remove_address, remove_address != '')                  as remove_addresses,
       uniqExactIf(gift_claiming_address, gift_claiming_address != '')    as claim_addresses,
       round(sum(gift_amount_gboot), 1)                                   as claim_amount_gboot,
       round(sum(released_gboot), 1)                                      as release_amount_gboot,
       uniqExactIf(signer, proof_address != '')                           as proof_signers,
       uniqExactIf(signer, remove_address != '')                          as remove_signers,
       uniqExactIf(signer, gift_claiming_address != '')                   as claim_signers,
       uniqExactIf(signer, released_gboot != 0 and release_address != '') as release_signers,
       uniqExactIf(message_contract, gift_amount_gboot != 0 or released_gboot != 0) as message_contract_cnt
FROM (
         SELECT signer,
                arrayJoin(JSONExtractArrayRaw(messages))                     as message_row,
                trim(BOTH '"' FROM
                     replaceAll(replaceAll(message_row, '\\', ''), '@', '')) as message,
                JSONExtractString(message, 'type')                           as message_type,
                JSONExtractString(message, 'sender')                         as message_sender,
                JSONExtractString(message, 'contract')                       as message_contract,
                JSONExtractString(message, 'msg')                            as message_msg,
                JSON_VALUE(message_msg, '$.proof_address.address')           as proof_address,
                JSON_VALUE(message_msg, '$.remove_address.address')          as remove_address,
                JSON_VALUE(message_msg, '$.release.gift_address')            as release_address,
                round(toInt64OrZero(JSON_VALUE(message_msg, '$.claim.gift_amount')) / 1e9,
                      1)                                                     as gift_amount_raw_gboot,
                JSON_VALUE(message_msg, '$.claim.gift_claiming_address')     as gift_claiming_address,
                toInt64OrZero(replace(JSON_VALUE(JSONExtractArrayRaw(raw_log)[1], '$.events[1].attributes[0].value'),
                                      'boot', '')) /
                1e9                                                          as released_gboot,
                toInt64OrZero(JSON_VALUE(JSONExtractArrayRaw(raw_log)[1], '$.events[5].attributes[4].value')) /
                1e9                                                          as gift_amount_gboot,
                date
         FROM (
                  SELECT height,
                         signer,
                         raw_log,
                         messages,
                         date
                  FROM `spacebox`.transaction FINAL
                           LEFT ANY
                           JOIN (
                      SELECT height,
                             toDate(timestamp) as date
                      FROM `spacebox`.block
                          PREWHERE block.height > 10800000) as b
                                ON transaction.height = b.height
                      PREWHERE transaction.height > 10800000 and transaction.success = true)
         WHERE message_type == '/cosmwasm.wasm.v1.MsgExecuteContract'
           and message_contract in ('bostrom1xut80d09q0tgtch8p0z4k5f88d3uvt8cvtzm5h3tu3tsy4jk9xlsfzhxel',
                                    'bostrom16t6tucgcqdmegye6c9ltlkr237z8yfndmasrhvh7ucrfuqaev6xq7cpvek')
         ORDER BY height DESC)
GROUP BY date
ORDER BY date;
