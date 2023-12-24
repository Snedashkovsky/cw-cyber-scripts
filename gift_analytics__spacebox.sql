SELECT date,
       sum(if(proof_address != '', 1, 0))         as proof_address_cnt,
       sum(if(remove_address != '', 1, 0))        as remove_address_cnt,
       sum(if(gift_claiming_address != '', 1, 0)) as gift_claiming_address_cnt,
       round(sum(gift_amount_gboot), 1)           as claim_amount_gboot,
       round(sum(released_gboot), 1)              as release_amount_gboot,
       uniqExactIf(signer, proof_address != '') as proof_address_signers,
       uniqExactIf(signer, remove_address != '') as remove_address_signers,
       uniqExactIf(signer, gift_claiming_address != '') as claim_address_signers,
       uniqExactIf(signer, released_gboot != 0) as release_address_signers
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
                  SELECT *
                  FROM `spacebox`.transaction
                           LEFT ANY
                           JOIN (
                      SELECT height,
                             toDate(timestamp) as date
                      FROM `spacebox`.block
                          PREWHERE block.height > 11100000) as b
                                ON transaction.height = b.height
                      PREWHERE transaction.height > 11100000 and transaction.success = true)
         WHERE message_type == '/cosmwasm.wasm.v1.MsgExecuteContract'
         ORDER BY height DESC
         LIMIT 1000000)
GROUP BY date
ORDER BY date;